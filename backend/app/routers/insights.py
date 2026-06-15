"""
insights.py
FastAPI router exposing endpoints for retrieving and managing system-generated
Insight nodes, including status updates and the analyst feedback loop.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.database.neo4j_client import neo4j_client
from backend.app.services.insight_engine import generate_insights_from_scan

logger = logging.getLogger("crimegpt.routers.insights")

router = APIRouter(prefix="/insights", tags=["Insights"])

# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class FeedbackRequest(BaseModel):
    feedback: str = Field(..., description="Analyst feedback value: 'confirmed' or 'false_positive'", examples=["confirmed"])

# ==============================================================================
# Router Endpoints
# ==============================================================================

@router.get("/", response_model=List[dict[str, Any]])
def list_insights_endpoint(
    severity: Optional[str] = None,
    type: Optional[str] = None,
    read: Optional[bool] = None,
    limit: int = 50
) -> List[dict[str, Any]]:
    """
    Retrieves all Insight nodes from Neo4j matching optional filters, sorted by generated_at descending.
    Appends the list of concerned case IDs.
    """
    conditions = ["coalesce(i.auto_suppressed, false) = false"]
    params = {"limit": limit}

    if severity is not None:
        conditions.append("i.severity = $severity")
        params["severity"] = severity
    if type is not None:
        conditions.append("i.type = $type")
        params["type"] = type
    if read is not None:
        conditions.append("i.read = $read")
        params["read"] = read

    where_clause = "WHERE " + " AND ".join(conditions)

    query = f"""
    MATCH (i:Insight)
    {where_clause}
    OPTIONAL MATCH (i)-[:CONCERNS]->(c:Case)
    RETURN i, collect(distinct c.case_id) as concerned_cases
    ORDER BY i.generated_at DESC
    LIMIT $limit
    """
    try:
        records = neo4j_client.execute_read(query, params)
        results = []
        for r in records:
            insight_node = r["i"]
            if insight_node:
                insight_data = dict(insight_node)
                insight_data["concerned_cases"] = r["concerned_cases"]
                results.append(insight_data)
        return results
    except Exception as e:
        logger.error(f"Error listing insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing insights: {str(e)}"
        )

@router.get("/summary", response_model=dict[str, Any])
def get_insights_summary_endpoint() -> dict[str, Any]:
    """
    Returns dashboard summary stats for unsuppressed insights in a single Cypher query.
    """
    query = """
    MATCH (i:Insight)
    WHERE coalesce(i.auto_suppressed, false) = false
    RETURN 
      count(i) as count,
      sum(CASE WHEN i.read = false THEN 1 ELSE 0 END) as unread,
      i.severity as severity,
      i.type as type,
      max(i.generated_at) as last_scan
    """
    try:
        records = neo4j_client.execute_read(query)
        
        total = 0
        unread = 0
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        by_type = {
            "recidivism_flag": 0,
            "location_cluster": 0,
            "shared_evidence": 0,
            "mo_pattern": 0
        }
        last_scan_at = None

        for r in records:
            cnt = r["count"]
            unr = r["unread"]
            sev = r["severity"]
            typ = r["type"]
            lst = r["last_scan"]

            total += cnt
            unread += unr
            if sev in by_severity:
                by_severity[sev] += cnt
            if typ in by_type:
                by_type[typ] += cnt
            if lst:
                if not last_scan_at or lst > last_scan_at:
                    last_scan_at = lst

        return {
            "total": total,
            "unread": unread,
            "by_severity": by_severity,
            "by_type": by_type,
            "last_scan_at": last_scan_at
        }
    except Exception as e:
        logger.error(f"Error generating insights summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating summary: {str(e)}"
        )

@router.patch("/{insight_id}/read", response_model=dict[str, Any])
def mark_insight_as_read_endpoint(insight_id: str) -> dict[str, Any]:
    """
    Marks a single insight node as read and returns the updated node.
    """
    query = """
    MATCH (i:Insight {insight_id: $insight_id})
    SET i.read = true
    WITH i
    OPTIONAL MATCH (i)-[:CONCERNS]->(c:Case)
    RETURN i, collect(distinct c.case_id) as concerned_cases
    """
    try:
        records = neo4j_client.execute_write(query, {"insight_id": insight_id})
        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insight with ID '{insight_id}' not found."
            )
        res = records[0]
        insight_data = dict(res["i"])
        insight_data["concerned_cases"] = res["concerned_cases"]
        return insight_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking insight read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking insight read: {str(e)}"
        )

@router.patch("/{insight_id}/feedback", response_model=dict[str, Any])
def submit_insight_feedback_endpoint(insight_id: str, payload: FeedbackRequest) -> dict[str, Any]:
    """
    Submits analyst feedback ('confirmed' or 'false_positive').
    If 'false_positive', suppresses all other similar unreviewed insights (auto_suppressed = true).
    """
    fb = payload.feedback.lower()
    if fb not in ["confirmed", "false_positive"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback must be either 'confirmed' or 'false_positive'."
        )

    feedback_at = datetime.now(timezone.utc).isoformat()
    
    # 1. Update the target insight
    update_query = """
    MATCH (i:Insight {insight_id: $insight_id})
    SET i.analyst_feedback = $feedback,
        i.feedback_at = $feedback_at,
        i.read = true
    WITH i
    OPTIONAL MATCH (i)-[:CONCERNS]->(c:Case)
    RETURN i, i.type as type, i.title as title, collect(distinct c.case_id) as concerned_cases
    """
    try:
        records = neo4j_client.execute_write(update_query, {
            "insight_id": insight_id,
            "feedback": fb,
            "feedback_at": feedback_at
        })
        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insight with ID '{insight_id}' not found."
            )
        
        res = records[0]
        insight_data = dict(res["i"])
        insight_data["concerned_cases"] = res["concerned_cases"]
        insight_type = res["type"]
        insight_title = res["title"]

        auto_suppressed_count = 0

        # 2. If false positive, suppress other identical insights
        if fb == "false_positive":
            suppress_query = """
            MATCH (other:Insight)
            WHERE other.type = $type
              AND other.title = $title
              AND other.analyst_feedback = 'none'
              AND other.insight_id <> $insight_id
            SET other.auto_suppressed = true,
                other.read = true
            RETURN count(other) as count
            """
            suppress_records = neo4j_client.execute_write(suppress_query, {
                "type": insight_type,
                "title": insight_title,
                "insight_id": insight_id
            })
            if suppress_records:
                auto_suppressed_count = suppress_records[0].get("count", 0)
                logger.info(f"Auto-suppressed {auto_suppressed_count} matching insights for title '{insight_title}'.")

        return {
            "updated_insight": insight_data,
            "auto_suppressed_count": auto_suppressed_count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting analyst feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting analyst feedback: {str(e)}"
        )

@router.post("/trigger-scan", response_model=dict[str, Any])
async def trigger_insight_scan_endpoint() -> dict[str, Any]:
    """
    Manually triggers an immediate full insight engine scan.
    """
    try:
        summary = await generate_insights_from_scan()
        return summary
    except Exception as e:
        logger.error(f"Error triggering manual insight scan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing insight scan: {str(e)}"
        )
