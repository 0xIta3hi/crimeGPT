"""
case_service.py
Service layer handling case creation, evidence logs, entity resolution
for persons/accused, and Cytoscape case graph visualization.
"""

import uuid
import logging
from typing import Any
from backend.app.database.neo4j_client import neo4j_client

logger = logging.getLogger("crimegpt.services.case_service")

class CaseService:
    """
    Handles business logic and database queries for Cases, Officers, Persons,
    Evidence, and Canonical Persons.
    """

    def create_case(self, case_id: str, fir_number: str, ps_code: str, officer_badge_id: str, rag_sections: Optional[list[str]] = None) -> dict[str, Any]:
        """
        Creates a new Case node, merges the Investigating Officer on badge_id,
        and establishes an INVESTIGATING link between them.
        """
        if rag_sections is None:
            rag_sections = ["303(2)", "305"]
            
        query = """
        MERGE (o:Officer {badge_id: $officer_badge_id})
        ON CREATE SET o.name = "Officer " + $officer_badge_id
        CREATE (c:Case {
            case_id: $case_id,
            fir_number: $fir_number,
            ps_code: $ps_code,
            status: "Investigation",
            rag_sections: $rag_sections
        })
        CREATE (o)-[:INVESTIGATING]->(c)
        RETURN c, o
        """
        try:
            records = neo4j_client.execute_write(query, {
                "officer_badge_id": officer_badge_id,
                "case_id": case_id,
                "fir_number": fir_number,
                "ps_code": ps_code,
                "rag_sections": rag_sections
            })
            if not records:
                raise RuntimeError("Failed to execute Neo4j write transaction to create Case.")
                
            return {
                "case_id": case_id,
                "fir_number": fir_number,
                "ps_code": ps_code,
                "officer_badge_id": officer_badge_id,
                "status": "created"
            }
        except Exception as e:
            logger.error(f"Error in create_case: {e}")
            raise e

    def add_person_to_case(self, case_id: str, name: str, role: str, aadhar_hash: str) -> dict[str, Any]:
        """
        Creates a new Person node unique to this case. Resolves this Person
        to a CanonicalPerson via their aadhar_hash, tracking aliases and case lists.
        Establishes RESOLVES_TO and ACCUSED_IN / VICTIM_IN edges.
        """
        person_canonical_id = str(uuid.uuid4())
        role_rel = "ACCUSED_IN" if role.lower() == "accused" else "VICTIM_IN"

        query = f"""
        MATCH (c:Case {{case_id: $case_id}})
        CREATE (p:Person {{
            canonical_id: $person_canonical_id,
            name: $name,
            case_id: $case_id,
            role: $role,
            aadhar_hash: $aadhar_hash
        }})
        CREATE (p)-[:{role_rel}]->(c)
        
        WITH p
        MERGE (cp:CanonicalPerson {{aadhar_hash: $aadhar_hash}})
        ON CREATE SET 
            cp.case_count = 1,
            cp.aliases = [$name],
            cp.case_ids = [$case_id],
            cp.first_seen_case = $case_id
        ON MATCH SET
            cp.case_count = cp.case_count + 1,
            cp.aliases = case when not $name in cp.aliases then cp.aliases + $name else cp.aliases end,
            cp.case_ids = case when not $case_id in cp.case_ids then cp.case_ids + $case_id else cp.case_ids end
        
        CREATE (p)-[:RESOLVES_TO]->(cp)
        RETURN cp.case_count AS case_count, cp.case_ids AS case_ids
        """
        try:
            records = neo4j_client.execute_write(query, {
                "case_id": case_id,
                "person_canonical_id": person_canonical_id,
                "name": name,
                "role": role,
                "aadhar_hash": aadhar_hash
            })
            if not records:
                raise RuntimeError(f"Failed to add person. Case '{case_id}' may not exist.")
            
            res = records[0]
            case_count = res.get("case_count", 1)
            case_ids = res.get("case_ids", [case_id])

            response = {
                "person_id": person_canonical_id,
                "name": name,
                "role": role,
                "aadhar_hash": aadhar_hash,
                "cross_case_alert": False,
                "linked_cases": []
            }

            if case_count > 1:
                response["cross_case_alert"] = True
                response["linked_cases"] = case_ids

            return response
        except Exception as e:
            logger.error(f"Error in add_person_to_case: {e}")
            raise e

    def add_evidence_to_case(self, case_id: str, description: str, evidence_type: str) -> dict[str, Any]:
        """
        Creates an Evidence node with a uuid and attaches it to the Case via a SEIZED_IN edge.
        """
        evidence_id = str(uuid.uuid4())
        query = """
        MATCH (c:Case {case_id: $case_id})
        CREATE (e:Evidence {
            evidence_id: $evidence_id,
            description: $description,
            type: $evidence_type
        })
        CREATE (e)-[:SEIZED_IN]->(c)
        RETURN e
        """
        try:
            records = neo4j_client.execute_write(query, {
                "case_id": case_id,
                "evidence_id": evidence_id,
                "description": description,
                "evidence_type": evidence_type
            })
            if not records:
                raise RuntimeError(f"Failed to add evidence. Case '{case_id}' may not exist.")

            return {
                "evidence_id": evidence_id,
                "description": description,
                "evidence_type": evidence_type,
                "case_id": case_id,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error in add_evidence_to_case: {e}")
            raise e

    def get_case_graph(self, case_id: str) -> dict[str, Any]:
        """
        Extracts the full 2-hop entity graph centered on this Case node.
        Returns a Cytoscape.js compatible dict with nodes and edges.
        """
        query = """
        MATCH (c:Case {case_id: $case_id})
        OPTIONAL MATCH (o:Officer)-[r_officer:INVESTIGATING]->(c)
        OPTIONAL MATCH (p:Person)-[r_person]->(c)
        WHERE type(r_person) IN ['ACCUSED_IN', 'VICTIM_IN']
        OPTIONAL MATCH (e:Evidence)-[r_evidence:SEIZED_IN]->(c)
        OPTIONAL MATCH (p)-[r_resolves:RESOLVES_TO]->(cp:CanonicalPerson)
        RETURN c, o, r_officer, p, r_person, e, r_evidence, r_resolves, cp
        """
        try:
            records = neo4j_client.execute_read(query, {"case_id": case_id})
            
            nodes_map = {}
            edges_map = {}

            # Helpers to avoid duplication and format cytoscape outputs
            def add_node(node_id: str, label: str, node_type: str, properties: dict[str, Any]) -> None:
                if node_id not in nodes_map:
                    nodes_map[node_id] = {
                        "data": {
                            "id": node_id,
                            "label": label,
                            "type": node_type,
                            **properties
                        }
                    }

            def add_edge(edge_id: str, source: str, target: str, edge_type: str) -> None:
                if edge_id not in edges_map:
                    edges_map[edge_id] = {
                        "data": {
                            "id": edge_id,
                            "source": source,
                            "target": target,
                            "label": edge_type
                        }
                    }

            for record in records:
                c = record.get("c")
                if not c:
                    continue

                # Add main Case Node
                add_node(c["case_id"], f"Case: {c['fir_number']}", "Case", {
                    "fir_number": c["fir_number"],
                    "ps_code": c["ps_code"]
                })

                # Process Investigating Officer
                o = record.get("o")
                r_officer = record.get("r_officer")
                if o and r_officer:
                    add_node(o["badge_id"], o.get("name", f"Officer: {o['badge_id']}"), "Officer", {
                        "badge_id": o["badge_id"],
                        "name": o.get("name"),
                        "rank": o.get("rank"),
                        "department": o.get("department")
                    })
                    add_edge(f"rel_{o['badge_id']}_{c['case_id']}", o["badge_id"], c["case_id"], "INVESTIGATING")

                # Process Incident Person (Accused / Victim)
                p = record.get("p")
                r_person = record.get("r_person")
                if p and r_person:
                    add_node(p["canonical_id"], p["name"], "Person", {
                        "canonical_id": p["canonical_id"],
                        "name": p["name"],
                        "role": p["role"],
                        "aadhar_hash": p.get("aadhar_hash")
                    })
                    add_edge(f"rel_{p['canonical_id']}_{c['case_id']}", p["canonical_id"], c["case_id"], type(r_person))

                    # Process CanonicalPerson Resolution links
                    cp = record.get("cp")
                    r_resolves = record.get("r_resolves")
                    if cp and r_resolves:
                        add_node(cp["aadhar_hash"], f"Canonical: {cp['aadhar_hash'][:6]}...", "CanonicalPerson", {
                            "aadhar_hash": cp["aadhar_hash"],
                            "aliases": cp.get("aliases", []),
                            "case_ids": cp.get("case_ids", []),
                            "case_count": cp.get("case_count", 0)
                        })
                        add_edge(f"rel_{p['canonical_id']}_{cp['aadhar_hash']}", p["canonical_id"], cp["aadhar_hash"], "RESOLVES_TO")

                # Process Case Evidence
                e = record.get("e")
                r_evidence = record.get("r_evidence")
                if e and r_evidence:
                    add_node(e["evidence_id"], e["description"], "Evidence", {
                        "evidence_id": e["evidence_id"],
                        "description": e["description"],
                        "type": e["type"]
                    })
                    add_edge(f"rel_{e['evidence_id']}_{c['case_id']}", e["evidence_id"], c["case_id"], "SEIZED_IN")

            return {
                "nodes": list(nodes_map.values()),
                "edges": list(edges_map.values())
            }
        except Exception as e:
            logger.error(f"Error in get_case_graph: {e}")
            raise e

# Singleton service instance
case_service = CaseService()
