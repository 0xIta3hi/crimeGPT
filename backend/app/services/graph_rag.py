import logging
from typing import Any, Optional
import spacy
from backend.app.config import settings
from backend.app.database.neo4j_client import neo4j_client

logger = logging.getLogger("crimegpt.services.graph_rag")

# Load spaCy model with graceful fallback if the model is not found
nlp = None
try:
    nlp = spacy.load(settings.SPACY_MODEL)
    logger.info(f"Loaded spaCy model '{settings.SPACY_MODEL}' successfully.")
except Exception as e:
    logger.warning(
        f"Could not load spaCy model '{settings.SPACY_MODEL}' due to: {e}. "
        f"Graph RAG will use fallback rule-based entity extraction. "
        f"To resolve, run: python -m spacy download {settings.SPACY_MODEL}"
    )

class GraphRAGService:
    """
    Service layer coordinating the Graph Retrieval-Augmented Generation (RAG) pipeline:
    1. Entity Extraction (NER) from narrative.
    2. Knowledge Graph context retrieval (Cypher queries).
    3. LLM System Prompt packaging.
    """

    async def process_and_query_rag(self, narrative: str) -> dict[str, Any]:
        """
        Main pipeline method to process crime narratives, retrieve relevant legal/FIR
        nodes from Neo4j, and compile the context for local LLM generation.
        """
        logger.info(f"Processing narrative: '{narrative[:60]}...'")

        # Step A: Entity Extraction
        entities = self._extract_entities(narrative)
        logger.debug(f"Extracted entities: {entities}")

        # Step B: Cypher query to retrieve BNS/BNSS nodes
        retrieved_nodes = await self._retrieve_knowledge_graph_nodes(entities)
        logger.debug(f"Retrieved nodes from Neo4j: {retrieved_nodes}")

        # Step C: Packaging into a system prompt context window block
        context_prompt = self._compile_system_prompt_context(narrative, entities, retrieved_nodes)

        return {
            "narrative": narrative,
            "extracted_entities": entities,
            "retrieved_nodes": retrieved_nodes,
            "system_prompt_context": context_prompt
        }

    def _extract_entities(self, narrative: str) -> dict[str, list[str]]:
        """
        Extracts entities (Accused, Location, Offense) from the narrative.
        Uses spaCy when available, with a regex/keyword fallback.
        """
        accused = []
        locations = []
        offenses = []

        if nlp:
            doc = nlp(narrative)
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    accused.append(ent.text)
                elif ent.label_ in ("GPE", "LOC", "FAC"):
                    locations.append(ent.text)
            
            # Simple keyword extraction for offenses (e.g. theft, assault, murder)
            lower_text = narrative.lower()
            known_offenses = ["theft", "burglary", "assault", "murder", "robbery", "fraud", "kidnapping", "cheating", "riot"]
            for off in known_offenses:
                if off in lower_text:
                    offenses.append(off.capitalize())
        else:
            # Fallback simple rule-based extractor
            # In a real environment, this extracts mock entities when spaCy is unavailable
            words = narrative.split()
            # Simple capitalized words check for Person/Location names as fallback
            for word in words:
                clean_word = word.strip(",.?!:;()\"'")
                if clean_word and clean_word[0].isupper() and clean_word.lower() not in ["the", "a", "an", "on", "in", "at", "by", "for", "with"]:
                    # Basic heuristic mapping to Accused or Location
                    if "street" in clean_word.lower() or "road" in clean_word.lower() or clean_word in ["Delhi", "Mumbai", "Bengaluru", "Kolkata"]:
                        locations.append(clean_word)
                    else:
                        accused.append(clean_word)
            
            lower_text = narrative.lower()
            known_offenses = ["theft", "burglary", "assault", "murder", "robbery", "fraud", "kidnapping", "cheating", "riot"]
            for off in known_offenses:
                if off in lower_text:
                    offenses.append(off.capitalize())

        # Deduplicate results
        return {
            "Accused": list(set(accused)),
            "Location": list(set(locations)),
            "Offense": list(set(offenses))
        }

    async def _retrieve_knowledge_graph_nodes(self, entities: dict[str, list[str]]) -> list[dict[str, Any]]:
        """
        Executes Cypher queries on Neo4j to retrieve relevant BNS (Bharatiya Nyaya Sanhita)
        and BNSS (Bharatiya Nagarik Suraksha Sanhita) sections matching extracted entities.
        """
        retrieved_nodes = []
        offenses = entities.get("Offense", [])
        locations = entities.get("Location", [])

        # If no offenses or locations were extracted, we can do a default fallback search
        search_terms = offenses + locations
        if not search_terms:
            logger.info("No query terms found. Returning empty node list.")
            return retrieved_nodes

        # Cypher query schema placeholder:
        # We search for BNS nodes (Sections) whose descriptions/names match our search terms,
        # along with connected BNSS nodes (Procedures).
        cypher_query = """
        UNWIND $terms AS term
        MATCH (bns:BNS_Section)
        WHERE toLower(bns.description) CONTAINS toLower(term) 
           OR toLower(bns.title) CONTAINS toLower(term)
        OPTIONAL MATCH (bns)-[r:PROCEDURE_GOVERNED_BY]->(bnss:BNSS_Section)
        RETURN bns.section_number AS section, 
               bns.title AS title, 
               bns.description AS description, 
               bns.punishment AS punishment,
               collect(bnss.section_number) AS associated_procedures
        LIMIT 10
        """

        try:
            # Execute the query using the thread-safe Neo4j Client helper.
            # This query is a parameterized read transaction.
            records = neo4j_client.execute_read(cypher_query, {"terms": search_terms})
            for record in records:
                retrieved_nodes.append({
                    "section": record.get("section"),
                    "title": record.get("title"),
                    "description": record.get("description"),
                    "punishment": record.get("punishment"),
                    "associated_procedures": record.get("associated_procedures", [])
                })
        except Exception as e:
            logger.error(f"Error querying Neo4j database: {e}")
            # Mock / stub fallback response for national security hackathon offline workspace testing
            logger.info("Returning mock/stub legal sections for offline hackathon testing.")
            retrieved_nodes = self._get_mock_legal_sections(offenses)

        return retrieved_nodes

    def _compile_system_prompt_context(
        self, narrative: str, entities: dict[str, list[str]], retrieved_nodes: list[dict[str, Any]]
    ) -> str:
        """
        Compiles narrative context, extracted entities, and retrieved legal provisions into
        a structured prompt segment for LLM instruction formatting.
        """
        entity_block = "\n".join(
            [f"- {category}: {', '.join(items) if items else 'None'}" for category, items in entities.items()]
        )

        legal_block_list = []
        for idx, node in enumerate(retrieved_nodes, 1):
            sec_num = node.get("section", "N/A")
            title = node.get("title", "Unknown Section")
            desc = node.get("description", "No description available.")
            punishment = node.get("punishment", "No punishment information.")
            proc = node.get("associated_procedures", [])
            proc_str = ", ".join(proc) if proc else "None"
            
            legal_block_list.append(
                f"{idx}. Section {sec_num}: {title}\n"
                f"   - Description: {desc}\n"
                f"   - Punishment: {punishment}\n"
                f"   - Associated BNSS Procedural Sections: {proc_str}"
            )
        legal_block = "\n".join(legal_block_list) if legal_block_list else "No matching BNS/BNSS legal provisions found."

        system_prompt = (
            "You are a professional legal assistant tool powered by CrimeGPT. "
            "You are reviewing the following offense narrative to prepare a Draft Charge Sheet.\n\n"
            "=== INPUT CRIME NARRATIVE ===\n"
            f"{narrative}\n\n"
            "=== EXTRACTED KEY ENTITIES ===\n"
            f"{entity_block}\n\n"
            "=== RETRIEVED LEGAL KNOWLEDGE (Neo4j BNS/BNSS Graph) ===\n"
            f"{legal_block}\n\n"
            "=== INSTRUCTION ===\n"
            "Analyze the crime narrative and the retrieved BNS/BNSS sections. "
            "Formulate a structured analysis detailing:\n"
            "1. Prime offenses committed.\n"
            "2. Applicable Bharatiya Nyaya Sanhita (BNS) section numbers.\n"
            "3. Required Bharatiya Nagarik Suraksha Sanhita (BNSS) investigative procedures to proceed."
        )

        return system_prompt

    def _get_mock_legal_sections(self, offenses: list[str]) -> list[dict[str, Any]]:
        """
        Helper returning mock legal sections if Neo4j is offline or empty during initialization.
        """
        mock_db = {
            "Theft": {
                "section": "303",
                "title": "Theft",
                "description": "Dishonestly taking moveable property out of the possession of any person without that person's consent.",
                "punishment": "Imprisonment of either description for a term which may extend to three years, or with fine, or with both.",
                "associated_procedures": ["BNSS-173 (Report of Police Officer)", "BNSS-182 (Search by Police Officer)"]
            },
            "Murder": {
                "section": "103",
                "title": "Murder",
                "description": "Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine.",
                "punishment": "Death penalty or life imprisonment, and liability of fine.",
                "associated_procedures": ["BNSS-174 (Inquest/Unnatural Death Report)", "BNSS-193 (Cognizance of Offence)"]
            },
            "Assault": {
                "section": "115",
                "title": "Voluntarily Causing Hurt",
                "description": "Whoever does any act with the intention of thereby causing hurt to any person, or with the knowledge that he is likely thereby to cause hurt.",
                "punishment": "Imprisonment for a term which may extend to one year, or with fine which may extend to ten thousand rupees, or with both.",
                "associated_procedures": ["BNSS-176 (Medical Examination of Victim)"]
            }
        }

        fallback_results = []
        found_any = False
        for off in offenses:
            if off in mock_db:
                fallback_results.append(mock_db[off])
                found_any = True

        if not found_any:
            # Default fallback section
            fallback_results.append({
                "section": "353",
                "title": "Criminal force or assault to deter public servant from discharge of his duty",
                "description": "Assaulting or using criminal force to any person being a public servant in the execution of his duty.",
                "punishment": "Imprisonment for a term which may extend to two years, or with fine, or with both.",
                "associated_procedures": ["BNSS-151 (Arrest to prevent cognizable offences)"]
            })

        return fallback_results

# Singleton service instance
graph_rag_service = GraphRAGService()
