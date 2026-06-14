"""
cases.py
FastAPI router endpoints exposing case management, entity registration,
evidence registration, and Cytoscape.js case graph visualization.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Any, Optional, List

from backend.app.services.case_service import case_service

router = APIRouter(prefix="/cases", tags=["cases"])

# ==============================================================================
# Pydantic Schemas for Requests
# ==============================================================================

class CaseCreateRequest(BaseModel):
    case_id: str = Field(..., description="Unique ID for the case / FIR reference", examples=["CASE-2026-001"])
    fir_number: str = Field(..., description="First Information Report number", examples=["FIR-12/2026"])
    ps_code: str = Field(..., description="Police Station Code", examples=["PS-DELHI-04"])
    officer_badge_id: str = Field(..., description="Badge ID of the Investigating Officer", examples=["BADGE-9901"])
    rag_sections: Optional[List[str]] = Field(None, description="Optional list of top BNS sections from RAG result")

class PersonAddRequest(BaseModel):
    name: str = Field(..., description="Full name of the individual", examples=["Rajesh Kumar"])
    role: str = Field(..., description="Role in the case: 'accused' or 'victim'", examples=["accused"])
    aadhar_hash: str = Field(..., description="Sha256 hash representing Aadhar ID for resolution", examples=["a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"])

class EvidenceAddRequest(BaseModel):
    description: str = Field(..., description="Description of the evidence piece", examples=["One silver laptop containing hacking scripts"])
    evidence_type: str = Field(..., description="Evidence type classification", examples=["Digital"])

# ==============================================================================
# Router Endpoints
# ==============================================================================

@router.get("/", response_model=List[dict[str, Any]])
def list_cases_endpoint() -> List[dict[str, Any]]:
    """
    Lists all Case nodes registered in the database.
    """
    try:
        return case_service.list_cases()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing cases: {str(e)}"
        )

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_case_endpoint(payload: CaseCreateRequest) -> dict[str, Any]:
    """
    Creates a new Case and links it to an Investigating Officer.
    """
    try:
        res = case_service.create_case(
            case_id=payload.case_id,
            fir_number=payload.fir_number,
            ps_code=payload.ps_code,
            officer_badge_id=payload.officer_badge_id,
            rag_sections=payload.rag_sections
        )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating case: {str(e)}"
        )

@router.post("/{case_id}/persons", status_code=status.HTTP_201_CREATED)
def add_person_endpoint(case_id: str, payload: PersonAddRequest) -> dict[str, Any]:
    """
    Adds a Person to a Case and performs Entity Resolution via Aadhar hash.
    Generates cross-case alerts if the individual is resolved to multiple cases.
    """
    try:
        res = case_service.add_person_to_case(
            case_id=case_id,
            name=payload.name,
            role=payload.role,
            aadhar_hash=payload.aadhar_hash
        )

        # Apply custom warning alerts on cross-case trigger
        if res.get("cross_case_alert"):
            other_cases = [cid for cid in res["linked_cases"] if cid != case_id]
            n = len(other_cases)
            res["alert_message"] = (
                f"WARNING: This individual has been linked to {n} other case(s). "
                f"Linked cases: {', '.join(other_cases)}"
            )
        
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering person: {str(e)}"
        )

@router.post("/{case_id}/evidence", status_code=status.HTTP_201_CREATED)
def add_evidence_endpoint(case_id: str, payload: EvidenceAddRequest) -> dict[str, Any]:
    """
    Registers a new piece of evidence and links it to the Case.
    """
    try:
        res = case_service.add_evidence_to_case(
            case_id=case_id,
            description=payload.description,
            evidence_type=payload.evidence_type
        )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering evidence: {str(e)}"
        )

@router.get("/{case_id}/graph")
def get_case_graph_endpoint(case_id: str) -> dict[str, Any]:
    """
    Retrieves the 2-hop Case Entity Graph formatted for Cytoscape.js canvas rendering.
    """
    try:
        res = case_service.get_case_graph(case_id=case_id)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving case graph: {str(e)}"
        )
