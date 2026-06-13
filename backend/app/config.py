from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Neo4j Database Settings
    NEO4J_URI: str = Field(default="bolt://localhost:7687", description="Neo4j Connection URI")
    NEO4J_USERNAME: str = Field(default="neo4j", description="Neo4j Database Username")
    NEO4J_PASSWORD: str = Field(default="password", description="Neo4j Database Password")
    NEO4J_DATABASE: str = Field(default="neo4j", description="Neo4j Target Database Name")

    # Local LLM / Generation Settings
    LOCAL_MODEL_ENDPOINT: str = Field(
        default="http://localhost:11434/v1", 
        description="Local LLM API Base URL (e.g. Ollama, LocalAI, vLLM)"
    )
    LOCAL_MODEL_NAME: str = Field(
        default="llama3", 
        description="Name of the model running on the local endpoint"
    )

    # OCR and NER Configuration
    TESSERACT_CMD: str = Field(default="/usr/bin/tesseract", description="Path to Tesseract executable")
    SPACY_MODEL: str = Field(default="en_core_web_sm", description="spaCy model name for NER processing")

    # General API Configuration
    PROJECT_NAME: str = "CrimeGPT"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")

    # Pydantic Settings Config to read from .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
