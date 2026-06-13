# CrimeGPT

CrimeGPT is a Graph Retrieval-Augmented Generation (Graph RAG) platform designed for national security and legal analysis. The platform combines a FastAPI backend, a Neo4j graph database, an offline OCR/NER ingestion layer, and a local LLM generation pipeline to process criminal case narratives and automatically map them to relevant legal statutes, sections, and procedural actions.

---

## 🏛 Project Architecture

CrimeGPT is structured as a mono-repository containing the following components:

- **`backend/`**: A FastAPI Python application handling application configurations, Neo4j database sessions, NLP/NER preprocessing, and service layer integration.
- **`frontend/`**: A React.js user interface designed for dashboards, case node visualizations, and interactive case file viewers.
- **`knowledge/`**: A storage bucket directory holding raw mock legal PDFs, First Information Reports (FIRs), and operational legal documents.

### Directory Tree

```text
crimeGPT/
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── api/              # API Route Handlers
│   │   ├── database/         # Database Clients (Neo4j Connection Manager)
│   │   ├── services/         # Business Logic (Graph RAG Orchestration)
│   │   ├── config.py         # Pydantic Configuration System
│   │   └── main.py           # FastAPI Application Entrypoint
│   └── requirements.txt      # Python Dependencies
├── frontend/                 # React.js Application
│   ├── src/
│   │   ├── components/       # Dashboards & Graph Canvas components
│   │   └── App.jsx
│   └── package.json
└── knowledge/                # Document Storage
    └── raw_pdfs/             # Mock legal and FIR PDFs
```

---

## 🚀 Getting Started

### Prerequisites

- **Python**: version 3.10 or higher
- **Node.js**: version 18 or higher (for the React frontend)
- **Neo4j Database**: Local installation or cloud instance (AuraDB)
- **Tesseract OCR**: (Optional) For offline text extraction from PDFs/images

---

### Backend Setup

1. **Navigate to the backend folder**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install spaCy NLP Model**:
   ```bash
   python -m spacy download en_core_web_sm
   ```

5. **Configure Environment Variables**:
   Create a `.env` file in the `backend/` directory:
   ```env
   # Neo4j Configurations
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your_password
   NEO4J_DATABASE=neo4j

   # Local LLM endpoint (Ollama / LocalAI / vLLM)
   LOCAL_MODEL_ENDPOINT=http://localhost:11434/v1
   LOCAL_MODEL_NAME=llama3
   ```

6. **Run the FastAPI Application**:
   ```bash
   PYTHONPATH=. uvicorn app.main:app --reload
   ```
   The backend will be served at `http://localhost:8000`. You can inspect the interactive OpenAPI documentation at `http://localhost:8000/docs`.

---

## 📡 API Reference

### 1. Health Status
Verify the server health and database connectivity.
* **URL**: `/health`
* **Method**: `GET`
* **Response**:
  ```json
  {
    "status": "healthy",
    "database_connected": true,
    "environment": "development"
  }
  ```

### 2. Graph RAG query
Process crime narrative text, extract entities, run Neo4j Cypher lookup, and package the LLM prompt.
* **URL**: `/api/v1/rag/query`
* **Method**: `POST`
* **Headers**: `Content-Type: application/json`
* **Request Body**:
  ```json
  {
    "narrative": "A suspect named John Doe stole a vehicle from Mahatma Gandhi Road."
  }
  ```
* **Response**:
  ```json
  {
    "narrative": "A suspect named John Doe stole a vehicle from Mahatma Gandhi Road.",
    "extracted_entities": {
      "Accused": ["John Doe"],
      "Location": ["Mahatma Gandhi Road"],
      "Offense": ["Theft"]
    },
    "retrieved_nodes": [
      {
        "section": "303",
        "title": "Theft",
        "description": "Dishonestly taking moveable property...",
        "punishment": "Imprisonment up to 3 years, fine, or both.",
        "associated_procedures": ["BNSS-173", "BNSS-182"]
      }
    ],
    "system_prompt_context": "..."
  }
  ```

---

## 🛠 Tech Stack

- **Backend**: FastAPI, Pydantic, spaCy (NER), PyTesseract (OCR), Python-Neo4j driver.
- **Frontend**: React, Vite, CSS, React Flow / Vis.js (for case graph visualization).
- **Database**: Neo4j (Graph Database) modeling relations between legal statutes (BNS) and criminal procedural acts (BNSS).
- **Local LLM Hosting**: Ollama / llama.cpp / vLLM.
