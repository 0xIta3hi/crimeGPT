"""
doc_generator.py
Service layer handling database queries for document types, hitting local Ollama
generation endpoints to build legal texts, and storing document records in Neo4j.
"""

import uuid
import json
import logging
import requests
from datetime import datetime, timezone
from typing import Any, Optional

from backend.app.database.neo4j_client import neo4j_client

logger = logging.getLogger("crimegpt.services.doc_generator")

# Supported document types
VALID_DOC_TYPES = {"fir_summary", "remand_request", "seizure_receipt"}

class DocumentGenerator:
    """
    Coordinates legal document generation from graph data context using local LLMs.
    """

    async def generate_document(self, case_id: str, doc_type: str) -> dict[str, Any]:
        """
        Main engine function:
        1. Fetch data from Neo4j according to doc_type.
        2. Construct LLM context and prompt.
        3. Call local Ollama model (phi3:mini).
        4. Parse and persist document node in Neo4j.
        5. Return document data dictionary.
        """
        if doc_type not in VALID_DOC_TYPES:
            raise ValueError(f"Invalid doc_type '{doc_type}'. Must be one of {VALID_DOC_TYPES}")

        logger.info(f"Generating document of type '{doc_type}' for case ID '{case_id}'...")

        # Step A: Graph Query Phase
        context_data = await self._fetch_graph_context(case_id, doc_type)
        if not context_data.get("case"):
            raise ValueError(f"Case with ID '{case_id}' not found in database.")

        # Step B: LLM Generation Phase
        llm_json = await self._generate_via_llm(context_data, doc_type)
        
        # Extract fields and stamp generation time
        title = llm_json.get("title", f"Generated {doc_type.replace('_', ' ').title()}")
        body = llm_json.get("body", "No content generated.")

        # Ensure title and body are strings (primitives) for Neo4j compatibility
        if not isinstance(title, str):
            if isinstance(title, (dict, list)):
                title = json.dumps(title, indent=2)
            else:
                title = str(title)

        if not isinstance(body, str):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, indent=2)
            else:
                body = str(body)

        generated_at = datetime.now(timezone.utc).isoformat()
        doc_id = str(uuid.uuid4())

        # Step C: Persist in Neo4j
        persist_query = """
        MATCH (c:Case {case_id: $case_id})
        CREATE (d:Document {
            doc_id: $doc_id,
            type: $doc_type,
            generated_at: $generated_at,
            title: $title,
            body: $body
        })
        CREATE (d)-[:GENERATED_FROM]->(c)
        RETURN d
        """
        try:
            neo4j_client.execute_write(persist_query, {
                "case_id": case_id,
                "doc_id": doc_id,
                "doc_type": doc_type,
                "generated_at": generated_at,
                "title": title,
                "body": body
            })
            logger.info(f"Successfully persisted Document node '{doc_id}' linked to Case '{case_id}'.")
        except Exception as e:
            logger.error(f"Error persisting Document node in Neo4j: {e}")
            raise e

        return {
            "doc_id": doc_id,
            "type": doc_type,
            "title": title,
            "body": body,
            "generated_at": generated_at,
            "case_id": case_id
        }

    async def _fetch_graph_context(self, case_id: str, doc_type: str) -> dict[str, Any]:
        """
        Queries Neo4j to compile custom contexts based on doc_type.
        """
        if doc_type == "fir_summary":
            query = """
            MATCH (c:Case {case_id: $case_id})
            OPTIONAL MATCH (o:Officer)-[:INVESTIGATING]->(c)
            OPTIONAL MATCH (p:Person)-[r_person]->(c)
            WHERE type(r_person) IN ['ACCUSED_IN', 'VICTIM_IN']
            OPTIONAL MATCH (e:Evidence)-[:SEIZED_IN]->(c)
            OPTIONAL MATCH (c)-[:CHARGED_UNDER]->(bns:BNS_Section)
            RETURN c, 
                   collect(distinct o) as officers, 
                   collect(distinct p) as persons, 
                   collect(distinct e) as evidence, 
                   collect(distinct bns) as charged_sections
            """
            records = neo4j_client.execute_read(query, {"case_id": case_id})
            if not records:
                return {}
            
            res = records[0]
            case_node = res.get("c")
            if not case_node:
                return {}

            charged_sections = res.get("charged_sections", [])
            # Fallback: if no CHARGED_UNDER sections, fetch from Case.rag_sections
            if not [s for s in charged_sections if s is not None]:
                rag_sections = case_node.get("rag_sections", [])
                if rag_sections:
                    bns_query = """
                    MATCH (b:BNS_Section)
                    WHERE b.section_id IN $rag_sections
                    RETURN b
                    """
                    bns_records = neo4j_client.execute_read(bns_query, {"rag_sections": rag_sections})
                    charged_sections = [rec.get("b") for rec in bns_records if rec.get("b") is not None]

            return {
                "case": case_node,
                "officer": res.get("officers")[0] if res.get("officers") else None,
                "persons": [p for p in res.get("persons", []) if p is not None],
                "evidence": [e for e in res.get("evidence", []) if e is not None],
                "sections": charged_sections
            }

        elif doc_type == "remand_request":
            query = """
            MATCH (c:Case {case_id: $case_id})
            OPTIONAL MATCH (o:Officer)-[:INVESTIGATING]->(c)
            OPTIONAL MATCH (p:Person)-[:ACCUSED_IN]->(c)
            OPTIONAL MATCH (p)-[:RESOLVES_TO]->(cp:CanonicalPerson)
            RETURN c, 
                   collect(distinct o) as officers, 
                   collect(distinct {person: p, canonical: cp}) as accused_history
            """
            records = neo4j_client.execute_read(query, {"case_id": case_id})
            if not records:
                return {}
            res = records[0]
            
            # Filter accused history records to exclude nulls
            accused_history = []
            for item in res.get("accused_history", []):
                if item and item.get("person") is not None:
                    accused_history.append(item)

            return {
                "case": res.get("c"),
                "officer": res.get("officers")[0] if res.get("officers") else None,
                "accused_history": accused_history
            }

        elif doc_type == "seizure_receipt":
            query = """
            MATCH (c:Case {case_id: $case_id})
            OPTIONAL MATCH (o:Officer)-[:INVESTIGATING]->(c)
            OPTIONAL MATCH (e:Evidence)-[:SEIZED_IN]->(c)
            RETURN c, 
                   collect(distinct o) as officers, 
                   collect(distinct e) as evidence
            """
            records = neo4j_client.execute_read(query, {"case_id": case_id})
            if not records:
                return {}
            res = records[0]
            return {
                "case": res.get("c"),
                "officer": res.get("officers")[0] if res.get("officers") else None,
                "evidence": [e for e in res.get("evidence", []) if e is not None]
            }

        return {}

    async def _generate_via_llm(self, context_data: dict[str, Any], doc_type: str) -> dict[str, str]:
        """
        Constructs context blocks, formats LLM prompts, and hits local Ollama endpoint.
        """
        # Compile document-specific context string
        case = context_data.get("case", {})
        officer = context_data.get("officer")
        
        if doc_type == "fir_summary":
            context_str = self._format_fir_summary_context(
                case, officer, context_data.get("persons", []), 
                context_data.get("evidence", []), context_data.get("sections", [])
            )
            prompt_instruction = (
                "Write a professional FIR Summary based on the provided case details, investigating officer, "
                "persons involved, evidence logged, and BNS legal sections. Structure the summary cleanly with sections."
            )
        elif doc_type == "remand_request":
            context_str = self._format_remand_request_context(
                case, officer, context_data.get("accused_history", [])
            )
            prompt_instruction = (
                "Write a formal Remand Request petition to be presented to the Magistrate, requesting police custody extension. "
                "Highlight the investigating officer details, accused details, and detail any prior criminal history "
                "or multi-case links (from the CanonicalPerson record) justifying further interrogation."
            )
        else:  # seizure_receipt
            context_str = self._format_seizure_receipt_context(
                case, officer, context_data.get("evidence", [])
            )
            prompt_instruction = (
                "Write an official Seizure Receipt log detailing items seized during investigation. "
                "Explicitly list every seized item description, type, and ID, and attribute them to the investigating officer."
            )

        system_prompt = (
            "You are a legal document generator for Indian law enforcement.\n"
            "Return ONLY a valid JSON object. No markdown. No explanation.\n"
            "The JSON object must have exactly these keys:\n"
            '- "title": document title string\n'
            '- "body": the full document text as a single string with \\n for line breaks\n'
            '- "generated_at": leave as empty string (filled by the service)'
        )

        user_prompt = (
            f"INSTRUCTION: {prompt_instruction}\n\n"
            f"STRUCTURED GRAPH CONTEXT:\n"
            f"{context_str}"
        )

        payload = {
            "model": "phi3:mini",
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "format": "json"
        }

        try:
            logger.info("Hitting Ollama generation endpoint for document writing...")
            response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=45)
            response.raise_for_status()
            data = response.json()
            llm_text = data.get("response", "").strip()
            
            # Parse response JSON
            parsed_json = json.loads(llm_text)
            return parsed_json
        except Exception as e:
            logger.error(f"Error generating document text via local LLM: {e}")
            # Fallback JSON structure if LLM generation or parsing fails
            return {
                "title": f"Draft {doc_type.replace('_', ' ').title()} - {case.get('fir_number', case_id)}",
                "body": (
                    f"Draft document of type '{doc_type}' could not be processed automatically by the LLM.\n"
                    f"Error details: {e}\n\n"
                    f"GRAPH CONTEXT DUMP:\n{context_str}"
                ),
                "generated_at": ""
            }

    # ==============================================================================
    # Context Formatting Helpers
    # ==============================================================================

    def _format_fir_summary_context(self, case: dict, officer: Optional[dict], persons: list, evidence: list, sections: list) -> str:
        lines = [
            "CASE DETAILS:",
            f"Case ID: {case.get('case_id')}",
            f"FIR Number: {case.get('fir_number')}",
            f"Police Station Code: {case.get('ps_code')}",
            f"Status: {case.get('status')}",
            "",
            "INVESTIGATING OFFICER:",
            f"Badge ID: {officer.get('badge_id') if officer else 'N/A'}",
            f"Name: {officer.get('name') if officer else 'N/A'}",
            "",
            "PERSONS INVOLVED:"
        ]
        for p in persons:
            lines.append(f"- Name: {p.get('name')}, Role: {p.get('role')}, Aadhar Hash: {p.get('aadhar_hash')}")
            
        lines.append("")
        lines.append("EVIDENCE LOGGED:")
        for e in evidence:
            lines.append(f"- Type: {e.get('type')}, Description: {e.get('description')}")
            
        lines.append("")
        lines.append("APPLICABLE BNS SECTIONS:")
        for s in sections:
            if s:
                lines.append(f"- Section {s.get('section_id')} - {s.get('title')}: {s.get('text')}")
                lines.append(f"  Punishment: {s.get('punishment')}")
            
        return "\n".join(lines)

    def _format_remand_request_context(self, case: dict, officer: Optional[dict], accused_history: list) -> str:
        lines = [
            "CASE DETAILS:",
            f"Case ID: {case.get('case_id')}",
            f"FIR Number: {case.get('fir_number')}",
            f"Police Station Code: {case.get('ps_code')}",
            "",
            "INVESTIGATING OFFICER:",
            f"Badge ID: {officer.get('badge_id') if officer else 'N/A'}",
            f"Name: {officer.get('name') if officer else 'N/A'}",
            "",
            "ACCUSED INDIVIDUALS & PRIOR RECORD HISTORY:"
        ]
        for item in accused_history:
            p = item.get("person")
            cp = item.get("canonical")
            if p:
                lines.append(f"- Name: {p.get('name')}")
                lines.append(f"  Aadhar Hash: {p.get('aadhar_hash')}")
                if cp:
                    lines.append(f"  Total Criminal Cases Linked: {cp.get('case_count', 0)}")
                    other_cases = [cid for cid in cp.get('case_ids', []) if cid != case.get('case_id')]
                    lines.append(f"  Other Linked Case IDs: {', '.join(other_cases) or 'None'}")
                else:
                    lines.append("  Total Criminal Cases Linked: 1")
                    lines.append("  Other Linked Case IDs: None")
                
        return "\n".join(lines)

    def _format_seizure_receipt_context(self, case: dict, officer: Optional[dict], evidence: list) -> str:
        lines = [
            "CASE DETAILS:",
            f"Case ID: {case.get('case_id')}",
            f"FIR Number: {case.get('fir_number')}",
            f"Police Station Code: {case.get('ps_code')}",
            "",
            "INVESTIGATING OFFICER:",
            f"Badge ID: {officer.get('badge_id') if officer else 'N/A'}",
            f"Name: {officer.get('name') if officer else 'N/A'}",
            "",
            "SEIZED ITEMS & EVIDENCE:"
        ]
        for idx, e in enumerate(evidence, 1):
            lines.append(f"{idx}. Item ID: {e.get('evidence_id')}")
            lines.append(f"   Type: {e.get('type')}")
            lines.append(f"   Description: {e.get('description')}")
            
        return "\n".join(lines)

# Singleton service instance
doc_generator = DocumentGenerator()
