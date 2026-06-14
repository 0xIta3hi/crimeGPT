"""
graph_rag.py
Graph RAG Service coordinating entity extraction, Neo4j context retrieval,
and local LLM structured JSON response generation.
"""

import json
import logging
import requests
from typing import Any, Optional

from backend.app.database.neo4j_client import neo4j_client

# Handle robust imports for ner_extractor
try:
    from backend.app.services.ner_extractor import extract_entities
except ImportError:
    try:
        from app.services.ner_extractor import extract_entities
    except ImportError:
        from .ner_extractor import extract_entities

logger = logging.getLogger("crimegpt.services.graph_rag")

# Hardcoded keyword to category mapping dict
KEYWORD_TO_CATEGORY = {
    "murder": "murder",
    "killed": "murder",
    "assault": "assault",
    "theft": "theft",
    "stolen": "theft",
    "robbery": "robbery",
    "kidnap": "kidnapping",
    "rape": "sexual offenses",
    "extortion": "extortion",
    "hack": "cybercrime",
    "fraud": "forgery",
    "forge": "forgery",
    "riot": "unlawful assembly"
}

class GraphRAGService:
    """
    Service coordinating the NLP extraction and Graph-based RAG pipeline.
    """

    async def process_and_query_rag(self, narrative: str) -> dict[str, Any]:
        """
        Executes the complete Graph RAG pipeline:
        1. Extract entities and offense keywords.
        2. Retrieve legal context from Neo4j based on offense categories.
        3. Formulate prompt context.
        4. Request structured output from local Ollama LLM.
        5. Parse response and format result.
        """
        logger.info(f"Initiating Graph RAG query for narrative: '{narrative[:60]}...'")

        # Step A: Entity extraction and mapping to offense categories
        entities = extract_entities(narrative)
        offense_keywords = entities.get("offense_keywords", [])
        
        # Determine offense categories to query
        categories = list(set(KEYWORD_TO_CATEGORY[kw] for kw in offense_keywords if kw in KEYWORD_TO_CATEGORY))
        logger.info(f"Extracted keywords: {offense_keywords} mapped to categories: {categories}")

        retrieved_nodes = []
        context_block = "LEGAL CONTEXT:\nNo matching legal provisions retrieved."

        # Step B: Query Neo4j for relevant legal context
        if categories:
            cypher_query = """
            MATCH (s:BNS_Section)
            WHERE s.offense_category IN $categories
            OPTIONAL MATCH (j:Judgment)-[:INTERPRETS]->(s)
            OPTIONAL MATCH (s)-[:CROSS_REFERENCES]->(related:BNS_Section)
            RETURN s.section_id AS section_id, 
                   s.title AS title, 
                   s.text AS text, 
                   s.punishment AS punishment,
                   collect(distinct j.citation) as judgments,
                   collect(distinct related.section_id) as related_sections
            """
            try:
                records = neo4j_client.execute_read(cypher_query, {"categories": categories})
                
                # Step C: Format retrieved provisions into the legal context block
                context_parts = ["LEGAL CONTEXT:"]
                for record in records:
                    sec_id = record.get("section_id")
                    title = record.get("title")
                    text = record.get("text")
                    punishment = record.get("punishment")
                    judgments = record.get("judgments", [])
                    related = record.get("related_sections", [])

                    # Store retrieved node info for response metadata
                    retrieved_nodes.append({
                        "section_id": sec_id,
                        "title": title,
                        "text": text,
                        "punishment": punishment,
                        "associated_judgments": judgments,
                        "related_sections": related
                    })

                    part = (
                        f"Section {sec_id} - {title}: {text}\n"
                        f"Punishment: {punishment}\n"
                        f"Relevant Judgments: {judgments}\n"
                        f"Related Sections: {related}"
                    )
                    context_parts.append(part)
                
                if len(context_parts) > 1:
                    context_block = "\n\n".join(context_parts)
                    
            except Exception as e:
                logger.error(f"Error querying Neo4j for categories: {categories}. Exception: {e}")
                context_block = "LEGAL CONTEXT:\nError retrieving matching legal provisions from database."

        # Step D: Request structured JSON analysis from Ollama local LLM
        system_prompt = (
            "You are a legal intelligence assistant for Indian law enforcement.\n"
            "Given an FIR narrative and retrieved legal context, return ONLY a valid JSON object with these keys:\n"
            '- "recommended_sections": list of section_id strings\n'
            '- "reasoning": one sentence explaining why\n'
            '- "required_documents": list of document names needed\n'
            '- "landmark_judgments": list of citation strings\n'
            "Do not include any text outside the JSON object."
        )
        
        user_prompt = f"FIR Narrative:\n{narrative}\n\n{context_block}"
        
        payload = {
            "model": "phi3:mini",
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "format": "json"
        }

        # Initialize base response mapping
        response_data = {
            "narrative": narrative,
            "extracted_entities": {
                "Accused": entities.get("persons", []),
                "Location": entities.get("locations", []),
                "Offense": offense_keywords
            },
            "retrieved_nodes": retrieved_nodes,
            "system_prompt_context": context_block
        }

        llm_text = ""
        try:
            logger.info("Querying local Ollama endpoint http://localhost:11434/api/generate...")
            response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=30)
            response.raise_for_status()
            llm_result = response.json()
            llm_text = llm_result.get("response", "").strip()
            logger.debug(f"Received raw Ollama response: {llm_text}")
        except Exception as e:
            logger.error(f"Ollama generation failed or timed out: {e}")
            response_data.update({
                "raw_response": f"Ollama Connection Error: {e}",
                "parse_error": True,
                "recommended_sections": [],
                "reasoning": "Failed to connect to local Ollama service.",
                "required_documents": [],
                "landmark_judgments": []
            })
            return response_data

        # Step E: Parse the JSON response
        try:
            parsed_json = json.loads(llm_text)
            response_data.update({
                "recommended_sections": parsed_json.get("recommended_sections", []),
                "reasoning": parsed_json.get("reasoning", ""),
                "required_documents": parsed_json.get("required_documents", []),
                "landmark_judgments": parsed_json.get("landmark_judgments", []),
                "parse_error": False
            })
        except Exception as parse_ex:
            logger.warning(f"Failed to parse Ollama JSON response: {parse_ex}. Raw text: '{llm_text}'")
            response_data.update({
                "raw_response": llm_text,
                "parse_error": True,
                "recommended_sections": [],
                "reasoning": "Could not parse structured analysis from local LLM.",
                "required_documents": [],
                "landmark_judgments": []
            })

        return response_data

# Singleton instance
graph_rag_service = GraphRAGService()
