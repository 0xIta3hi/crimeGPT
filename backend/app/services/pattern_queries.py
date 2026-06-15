"""
pattern_queries.py
Service layer exposing Cypher-based legal intelligence pattern queries
for Repeat Offenders (Recidivism), Location Clusters (Hotspots),
Shared Evidence signals, and Modus Operandi (MO) patterns.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from backend.app.database.neo4j_client import neo4j_client

logger = logging.getLogger("crimegpt.services.pattern_queries")

def detect_recidivism() -> list[dict[str, Any]]:
    """
    Identifies repeat offenders (CanonicalPerson nodes appearing as accused
    in 2 or more distinct cases) and return their case lists and dates.
    """
    logger.info("Scanning database for repeat offenders (Recidivism)...")
    query = """
    MATCH (cp:CanonicalPerson)
    WHERE cp.case_count >= 2
    MATCH (p:Person)-[:RESOLVES_TO]->(cp)
    MATCH (p)-[:ACCUSED_IN]->(c:Case)
    RETURN 
      cp.aadhar_hash as aadhar_hash,
      cp.aliases as aliases,
      cp.case_count as case_count,
      cp.case_ids as case_ids,
      collect(distinct c.date_filed) as offense_dates
    ORDER BY cp.case_count DESC
    """
    try:
        return neo4j_client.execute_read(query)
    except Exception as e:
        logger.error(f"Error executing detect_recidivism query: {e}")
        return []

def detect_location_clusters(threshold: int = 3, days: int = 90) -> list[dict[str, Any]]:
    """
    Identifies geographic hotspots (locations with case occurrences matching or
    exceeding the threshold within the specified window of days).
    """
    logger.info(f"Scanning database for location clusters (hotspots) in last {days} days...")
    # c.date_filed is stored as a string (YYYY-MM-DD), so we parse it as a date in Cypher
    query = """
    MATCH (c:Case)-[:OCCURRED_AT]->(l:Location)
    WHERE c.date_filed IS NOT NULL 
      AND date(c.date_filed) >= date() - duration({days: $days})
    WITH l.address as location, collect(distinct c.case_id) as cases, count(distinct c) as case_count
    WHERE case_count >= $threshold
    RETURN location, cases, case_count
    ORDER BY case_count DESC
    """
    try:
        return neo4j_client.execute_read(query, {"days": days, "threshold": threshold})
    except Exception as e:
        logger.error(f"Error executing detect_location_clusters query: {e}")
        return []

def detect_shared_evidence() -> list[dict[str, Any]]:
    """
    Identifies evidence linked to multiple cases (based on identical description).
    Falls back gracefully to Python-side deduplication if APOC is not available.
    """
    logger.info("Scanning database for shared evidence signals...")
    
    # Try using APOC
    query_apoc = """
    MATCH (e1:Evidence)-[:SEIZED_IN]->(c1:Case)
    MATCH (e2:Evidence)-[:SEIZED_IN]->(c2:Case)
    WHERE c1.case_id < c2.case_id
      AND toLower(e1.description) = toLower(e2.description)
    WITH e1.description as evidence_description,
         collect(distinct c1.case_id) + collect(distinct c2.case_id) as raw_cases
    WITH evidence_description, apoc.coll.toSet(raw_cases) as linked_cases
    RETURN evidence_description, linked_cases, size(linked_cases) as case_count
    ORDER BY case_count DESC
    """
    try:
        return neo4j_client.execute_read(query_apoc)
    except Exception as e:
        logger.warning(f"APOC function call not available: {e}. Falling back to Python deduplication...")
        
        # Fallback query without APOC
        query_fallback = """
        MATCH (e1:Evidence)-[:SEIZED_IN]->(c1:Case)
        MATCH (e2:Evidence)-[:SEIZED_IN]->(c2:Case)
        WHERE c1.case_id < c2.case_id
          AND toLower(e1.description) = toLower(e2.description)
        RETURN e1.description as evidence_description,
               collect(distinct c1.case_id) as cases1,
               collect(distinct c2.case_id) as cases2
        """
        try:
            records = neo4j_client.execute_read(query_fallback)
            
            groups = {}
            for r in records:
                desc = r["evidence_description"]
                key = desc.lower()
                if key not in groups:
                    groups[key] = {"evidence_description": desc, "cases": set()}
                groups[key]["cases"].update(r.get("cases1", []))
                groups[key]["cases"].update(r.get("cases2", []))
                
            results = []
            for group in groups.values():
                linked_cases = list(group["cases"])
                results.append({
                    "evidence_description": group["evidence_description"],
                    "linked_cases": linked_cases,
                    "case_count": len(linked_cases)
                })
            # Sort by case_count DESC
            results.sort(key=lambda x: x["case_count"], reverse=True)
            return results
        except Exception as fallback_e:
            logger.error(f"Error executing detect_shared_evidence fallback: {fallback_e}")
            return []

def detect_mo_patterns(min_cases: int = 2) -> list[dict[str, Any]]:
    """
    Identifies Modus Operandi (MO) clusters. Tries querying (Case)-[:INVOLVES]->(Offense)
    first, falling back to direct Case node properties matching the seeded schema.
    """
    logger.info("Scanning database for Modus Operandi (MO) patterns...")
    
    # Try the specified schema (Case)-[:INVOLVES]->(Offense)
    query_involves = """
    MATCH (c:Case)-[:INVOLVES]->(o:Offense)
    WITH o.modus_operandi as modus_operandi,
         o.offense_category as category,
         collect(distinct c.case_id) as cases,
         count(distinct c) as case_count
    WHERE case_count >= $min_cases
      AND modus_operandi IS NOT NULL
    RETURN modus_operandi, category, cases, case_count
    ORDER BY case_count DESC
    """
    try:
        records = neo4j_client.execute_read(query_involves, {"min_cases": min_cases})
        if records:
            return records
    except Exception as e:
        logger.warning(f"INVOLVES relationship query failed: {e}. Trying direct Case properties...")

    # Fallback/default query: modus_operandi and category on the Case node directly
    logger.debug("Falling back to direct Case node properties for MO pattern scan.")
    query_direct = """
    MATCH (c:Case)
    WHERE c.modus_operandi IS NOT NULL
    WITH c.modus_operandi as modus_operandi,
         c.offense_category as category,
         collect(distinct c.case_id) as cases,
         count(distinct c) as case_count
    WHERE case_count >= $min_cases
    RETURN modus_operandi, category, cases, case_count
    ORDER BY case_count DESC
    """
    try:
        return neo4j_client.execute_read(query_direct, {"min_cases": min_cases})
    except Exception as e:
        logger.error(f"Error executing detect_mo_patterns query: {e}")
        return []

def run_all_pattern_scans() -> dict[str, Any]:
    """
    Orchestrates all four scans and compiles their results with execution timestamp.
    """
    logger.info("Orchestrating full pattern detection scan...")
    return {
        "recidivism": detect_recidivism(),
        "location_clusters": detect_location_clusters(),
        "shared_evidence": detect_shared_evidence(),
        "mo_patterns": detect_mo_patterns(),
        "scanned_at": datetime.now(timezone.utc).isoformat()
    }
