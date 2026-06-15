"""
insight_engine.py
Insight Engine Service coordinating the generation and persistence of
analytical Insight nodes in Neo4j based on scans and system events.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from backend.app.database.neo4j_client import neo4j_client
from backend.app.services.pattern_queries import run_all_pattern_scans

logger = logging.getLogger("crimegpt.services.insight_engine")

def check_insight_exists(insight_type: str, title: str) -> bool:
    """
    Checks if an unread, unreviewed insight of the same type and title already exists.
    """
    query = """
    MATCH (i:Insight {type: $type, title: $title, read: false, analyst_feedback: 'none'})
    RETURN count(i) > 0 as exists
    """
    try:
        records = neo4j_client.execute_read(query, {"type": insight_type, "title": title})
        if records:
            return records[0].get("exists", False)
    except Exception as e:
        logger.error(f"Error checking insight existence: {e}")
    return False

def create_insight_and_links(insight_id: str, insight_type: str, severity: str, title: str, description: str, triggered_by: str, case_ids: list[str]) -> dict[str, Any]:
    """
    Creates an Insight node and establishes CONCERNS relationships with case nodes.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    query = """
    CREATE (i:Insight {
        insight_id: $insight_id,
        type: $type,
        severity: $severity,
        title: $title,
        description: $description,
        generated_at: $generated_at,
        read: false,
        triggered_by: $triggered_by,
        analyst_feedback: 'none'
    })
    WITH i
    UNWIND $case_ids as cid
    MATCH (c:Case {case_id: cid})
    CREATE (i)-[:CONCERNS]->(c)
    RETURN i
    """
    params = {
        "insight_id": insight_id,
        "type": insight_type,
        "severity": severity,
        "title": title,
        "description": description,
        "generated_at": generated_at,
        "triggered_by": triggered_by,
        "case_ids": case_ids
    }
    try:
        neo4j_client.execute_write(query, params)
        return {
            "insight_id": insight_id,
            "type": insight_type,
            "severity": severity,
            "title": title,
            "description": description,
            "generated_at": generated_at,
            "read": False,
            "triggered_by": triggered_by,
            "analyst_feedback": "none"
        }
    except Exception as e:
        logger.error(f"Error persisting Insight node '{insight_id}': {e}")
        raise e

async def generate_insights_from_scan() -> dict[str, Any]:
    """
    Scheduler-invoked task running queries and populating Insight nodes.
    """
    logger.info("Executing scheduled Insight Engine scan...")
    scan_results = run_all_pattern_scans()
    
    created_count = 0
    skipped_count = 0
    
    breakdown = {
        "recidivism": 0,
        "location_cluster": 0,
        "shared_evidence": 0,
        "mo_pattern": 0
    }
    
    # 1. Recidivism Insights
    for r in scan_results.get("recidivism", []):
        aliases = r.get("aliases", [])
        case_count = r.get("case_count", 0)
        case_ids = r.get("case_ids", [])
        offense_dates = r.get("offense_dates", [])
        
        title = f"Repeat Offender Detected: {aliases[0]}"
        description = f"Individual known by aliases {aliases} has appeared as accused in {case_count} cases (IDs: {case_ids}). Latest offense dates: {offense_dates}."
        severity = "high" if case_count >= 3 else "medium"
        insight_type = "recidivism_flag"
        
        if check_insight_exists(insight_type, title):
            skipped_count += 1
            continue
            
        create_insight_and_links(
            insight_id=str(uuid.uuid4()),
            insight_type=insight_type,
            severity=severity,
            title=title,
            description=description,
            triggered_by="scheduler",
            case_ids=case_ids
        )
        created_count += 1
        breakdown["recidivism"] += 1

    # 2. Location Cluster Insights
    for l in scan_results.get("location_clusters", []):
        location = l.get("location", "")
        cases = l.get("cases", [])
        case_count = l.get("case_count", 0)
        
        title = f"Crime Cluster Detected: {location}"
        description = f"{case_count} cases have been filed at {location} in the last 90 days. Coordinated patrolling recommended."
        severity = "critical" if case_count >= 10 else ("high" if case_count >= 5 else "medium")
        insight_type = "location_cluster"
        
        if check_insight_exists(insight_type, title):
            skipped_count += 1
            continue
            
        create_insight_and_links(
            insight_id=str(uuid.uuid4()),
            insight_type=insight_type,
            severity=severity,
            title=title,
            description=description,
            triggered_by="scheduler",
            case_ids=cases
        )
        created_count += 1
        breakdown["location_cluster"] += 1

    # 3. Shared Evidence Insights
    for e in scan_results.get("shared_evidence", []):
        evidence_description = e.get("evidence_description", "")
        linked_cases = e.get("linked_cases", [])
        case_count = e.get("case_count", 0)
        
        title = f"Shared Evidence Signal: {evidence_description}"
        description = f"'{evidence_description}' appears as evidence in {case_count} separate cases (IDs: {linked_cases}). These cases may be linked."
        severity = "high" if case_count >= 3 else "medium"
        insight_type = "shared_evidence"
        
        if check_insight_exists(insight_type, title):
            skipped_count += 1
            continue
            
        create_insight_and_links(
            insight_id=str(uuid.uuid4()),
            insight_type=insight_type,
            severity=severity,
            title=title,
            description=description,
            triggered_by="scheduler",
            case_ids=linked_cases
        )
        created_count += 1
        breakdown["shared_evidence"] += 1

    # 4. MO Pattern Insights
    for m in scan_results.get("mo_patterns", []):
        modus_operandi = m.get("modus_operandi", "")
        category = m.get("category", "")
        cases = m.get("cases", [])
        case_count = m.get("case_count", 0)
        
        title = f"Emerging MO Pattern: {modus_operandi}"
        description = f"{case_count} {category} cases share the same modus operandi: '{modus_operandi}'. Cases: {cases}. Consider whether these are linked incidents."
        severity = "high" if case_count >= 5 else "medium"
        insight_type = "mo_pattern"
        
        if check_insight_exists(insight_type, title):
            skipped_count += 1
            continue
            
        create_insight_and_links(
            insight_id=str(uuid.uuid4()),
            insight_type=insight_type,
            severity=severity,
            title=title,
            description=description,
            triggered_by="scheduler",
            case_ids=cases
        )
        created_count += 1
        breakdown["mo_pattern"] += 1

    summary = {
        "insights_created": created_count,
        "insights_skipped_duplicate": skipped_count,
        "breakdown": breakdown,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    logger.info(f"Insight scan execution summary: {summary}")
    return summary

def generate_insight_for_person_event_sync(aadhar_hash: str, case_id: str) -> Optional[dict[str, Any]]:
    """
    Synchronous helper for event-triggered insight generation when a repeat offender
    is added to a case.
    """
    logger.info(f"Checking for repeat offender event-triggered insight for Aadhar '{aadhar_hash}' on Case '{case_id}'...")
    
    query_cp = """
    MATCH (cp:CanonicalPerson {aadhar_hash: $aadhar_hash})
    RETURN cp.aliases as aliases, cp.case_count as case_count, cp.case_ids as case_ids
    """
    try:
        records = neo4j_client.execute_read(query_cp, {"aadhar_hash": aadhar_hash})
        if not records:
            return None
            
        cp_data = records[0]
        aliases = cp_data.get("aliases", [])
        case_count = cp_data.get("case_count", 0)
        case_ids = cp_data.get("case_ids", [])
        
        if case_count < 2:
            return None
            
        title = f"ALERT: Known Repeat Offender Added to Case {case_id}"
        other_cases = [cid for cid in case_ids if cid != case_id]
        description = f"Individual with aliases {aliases} was just added to Case {case_id}. This individual has prior records in {case_count - 1} other case(s): {other_cases}."
        severity = "critical" if case_count >= 3 else "high"
        insight_type = "recidivism_flag"
        
        if check_insight_exists(insight_type, title):
            logger.info("Event-triggered repeat offender insight already exists. Skipping creation.")
            return None
            
        insight = create_insight_and_links(
            insight_id=str(uuid.uuid4()),
            insight_type=insight_type,
            severity=severity,
            title=title,
            description=description,
            triggered_by="new_person_event",
            case_ids=case_ids
        )
        logger.info(f"Successfully generated repeat offender insight alert: {title}")
        return insight
    except Exception as e:
        logger.error(f"Error in generate_insight_for_person_event_sync: {e}")
        return None

async def generate_insight_for_person_event(aadhar_hash: str, case_id: str) -> Optional[dict[str, Any]]:
    """
    Event-triggered version (asynchronous wrapper).
    """
    return generate_insight_for_person_event_sync(aadhar_hash, case_id)
