import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.database.neo4j_client import neo4j_client
from backend.app.services.graph_rag import graph_rag_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("crimegpt.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown events, specifically
    initializing and cleaning up database connections.
    """
    logger.info("Initializing CrimeGPT Backend Lifespan...")
    
    # Connect to Neo4j
    try:
        neo4j_client.connect()
        logger.info("Neo4j database connection established successfully.")
    except Exception as e:
        logger.error(
            f"Could not establish connection to Neo4j database during startup: {e}. "
            "App starting in offline / mock fallback mode."
        )

    yield

    # Clean up Neo4j
    logger.info("Tearing down CrimeGPT Backend Lifespan...")
    neo4j_client.close()
    logger.info("Neo4j database connection closed.")

# Initialize FastAPI App with metadata and lifespan
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend services for CrimeGPT national security Graph RAG system.",
    version="1.0.0",
    lifespan=lifespan
)

# Set up CORS middleware for frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.app.routers.cases import router as cases_router
app.include_router(cases_router, prefix=settings.API_V1_STR)

from typing import Optional

# API Schemas
class RAGQueryRequest(BaseModel):
    narrative: str = Field(
        ..., 
        description="The case narrative or FIR report text to analyze.",
        examples=["A suspect wearing a black hoodie stole a bag from Mahatma Gandhi Road."]
    )

class RAGQueryResponse(BaseModel):
    narrative: str
    extracted_entities: dict[str, list[str]]
    retrieved_nodes: list[dict]
    system_prompt_context: str
    recommended_sections: Optional[list[str]] = None
    reasoning: Optional[str] = None
    required_documents: Optional[list[str]] = None
    landmark_judgments: Optional[list[str]] = None
    raw_response: Optional[str] = None
    parse_error: Optional[bool] = None

# API Endpoints
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Simple health check endpoint verifying server status and database connectivity.
    """
    database_connected = False
    try:
        neo4j_client.verify_connectivity()
        database_connected = True
    except Exception:
        pass

    return {
        "status": "healthy",
        "database_connected": database_connected,
        "environment": settings.ENVIRONMENT
    }

@app.post(
    f"{settings.API_V1_STR}/rag/query", 
    response_model=RAGQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query the Graph RAG pipeline with a case narrative"
)
async def query_rag(payload: RAGQueryRequest):
    """
    Accepts a case narrative, runs entity extraction, retrieves context from Neo4j,
    and returns packaged system prompt context for LLM execution.
    """
    if not payload.narrative.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Narrative query parameter cannot be empty."
        )
    
    try:
        result = await graph_rag_service.process_and_query_rag(payload.narrative)
        return result
    except Exception as e:
        logger.error(f"Error executing Graph RAG query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the Graph RAG request."
        )
