"""
documents.py
FastAPI router endpoints for generating legal documents, fetching specific documents,
and listing all documents generated for a particular case.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Any, List

from backend.app.services.doc_generator import doc_generator
from backend.app.database.neo4j_client import neo4j_client

router = APIRouter(tags=["documents"])

# ==============================================================================
# Pydantic Schemas for Requests and Responses
# ==============================================================================

class DocumentGenerateRequest(BaseModel):
    case_id: str = Field(..., description="The Case ID to retrieve context data for", examples=["TEST-CASE-1"])
    doc_type: str = Field(..., description="Document type to generate: 'fir_summary', 'remand_request', or 'seizure_receipt'", examples=["fir_summary"])

class DocumentResponse(BaseModel):
    doc_id: str
    type: str
    title: str
    body: str
    generated_at: str
    case_id: str

# ==============================================================================
# Router Endpoints
# ==============================================================================

@router.post("/documents/generate", status_code=status.HTTP_201_CREATED, response_model=DocumentResponse)
async def generate_document_endpoint(payload: DocumentGenerateRequest):
    """
    Generates a new legal document using context retrieved from Neo4j and a local LLM prompt,
    storing the resulting Document node in Neo4j and linking it to the Case.
    """
    try:
        res = await doc_generator.generate_document(
            case_id=payload.case_id,
            doc_type=payload.doc_type
        )
        return res
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating document: {str(e)}"
        )

@router.get("/documents/{doc_id}", response_model=DocumentResponse)
def get_document_endpoint(doc_id: str):
    """
    Retrieves a previously generated Document node by its unique doc_id.
    """
    query = """
    MATCH (d:Document {doc_id: $doc_id})
    OPTIONAL MATCH (d)-[:GENERATED_FROM]->(c:Case)
    RETURN d, c.case_id AS case_id
    """
    try:
        records = neo4j_client.execute_read(query, {"doc_id": doc_id})
        if not records or not records[0].get("d"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{doc_id}' not found."
            )
        
        res = records[0]
        d = res.get("d")
        case_id = res.get("case_id") or ""
        
        return {
            "doc_id": d["doc_id"],
            "type": d["type"],
            "title": d["title"],
            "body": d["body"],
            "generated_at": d["generated_at"],
            "case_id": case_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving document: {str(e)}"
        )

@router.get("/cases/{case_id}/documents", response_model=List[DocumentResponse])
def get_case_documents_endpoint(case_id: str):
    """
    Lists all legal documents generated and registered for a specific Case ID.
    """
    query = """
    MATCH (d:Document)-[:GENERATED_FROM]->(c:Case {case_id: $case_id})
    RETURN d ORDER BY d.generated_at DESC
    """
    try:
        records = neo4j_client.execute_read(query, {"case_id": case_id})
        documents = []
        for record in records:
            d = record.get("d")
            if d:
                documents.append({
                    "doc_id": d["doc_id"],
                    "type": d["type"],
                    "title": d["title"],
                    "body": d["body"],
                    "generated_at": d["generated_at"],
                    "case_id": case_id
                })
        return documents
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving case documents: {str(e)}"
        )
