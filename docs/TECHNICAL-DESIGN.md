# ProofLens AI — Technical Design Document (TDD)

**Document ID:** PLAI-TDD-001  
**Version:** 1.0 — Phase 0 Baseline  
**Status:** Under Review (Awaiting Phase 1 Authorization)  
**Target Product:** ProofLens AI — From Documents to Verifiable Answers  
**Author:** AI Technical Architecture  

---

## 1. Project Goals, Scope, Assumptions, Constraints, and Non-Goals

### 1.1 Project Goals
1. Deliver a production-grade, college-presentable web application demonstrating evidence-first document intelligence.
2. Ingest multi-page PDF documents while strictly preserving document and page-level provenance.
3. Provide semantic retrieval across workspace documents backed by PostgreSQL with the `pgvector` extension.
4. Generate grounded natural-language answers strictly constrained to retrieved evidence passages, including programmatic server-side citation validation.
5. Provide deterministic abstention and explicit uncertainty communication when retrieved context is insufficient or contradictory.
6. Support cross-document comparison across two or more selected documents, producing per-document findings, agreement/contradiction notes, and direct passage citations.
7. Maintain a reproducible, automated evaluation suite measuring retrieval hit rate, citation validity, and negative/abstention query handling.
8. Maintain a modular, decoupled architecture enabling future evolution (e.g., agentic workflows, background workers) without core rewrites.

### 1.2 Scope (MVP Milestone)
- **Workspaces:** Single-tenant workspace abstraction to organize uploaded document collections.
- **Document Ingestion:** Text-based PDF extraction preserving page numbers, byte size, file hash, and chunk indices.
- **Vector Search:** Dense vector embeddings persisted in PostgreSQL using `pgvector` with cosine similarity (`vector_cosine_ops`).
- **Grounded Q&A:** LLM prompt template enforcing strict citation markers (`[Doc: <id>, Page: <p>]`) paired with post-generation server-side validation against retrieved candidate chunks.
- **Evidence Inspector:** Frontend modal/drawer allowing users to inspect exact source excerpts and page locations.
- **Cross-Document Comparison:** Side-by-side claim synthesis across user-selected document subsets.
- **Evaluation CLI:** Automated test script running curated question-answer-evidence fixtures and reporting metrics.

### 1.3 Assumptions
*Explicit engineering assumptions (not directly mandated by PRD, but established for architectural clarity):*
- **A-01: Document Type:** MVP will exclusively process digital text PDFs. Scanned image-only PDFs without an embedded text layer will be detected and flagged with a clear user-facing error (`UNSUPPORTED_SCANNED_PDF`).
- **A-02: LLM & Embedding Defaults:** OpenAI API (`gpt-4o-mini` for generation, `text-embedding-3-small` with 1536 dimensions for embeddings) is recommended as the default provider due to low latency, cost efficiency, and structured output support. An abstract provider interface will ensure compatibility with Gemini or local HuggingFace models without code changes.
- **A-03: Storage Strategy:** Original PDF files are stored on the local filesystem under an isolated `storage/uploads/` directory during MVP development. File records store relative paths and SHA-256 hashes.
- **A-04: User Authentication:** For the college portfolio presentation, the MVP operates in single-user demo mode (a default workspace or client-generated workspace ID) without multi-tenant authentication overhead.
- **A-05: Ingestion Execution:** Synchronous/FastAPI background tasks are sufficient for PDFs under 10MB (typically < 50 pages). Ingestion progress is tracked via database status states (`PENDING`, `PARSING`, `INDEXING`, `READY`, `FAILED`).

### 1.4 Constraints
- **C-01:** Backend runtime: Python 3.11+ (Host system verified: Python 3.13.5).
- **C-02:** Backend framework: FastAPI with Pydantic v2 schemas.
- **C-03:** Database: PostgreSQL 17 (Host verified: PostgreSQL 17.11 running) with `pgvector`.
- **C-04:** Migrations: Alembic for versioned schema and extension tracking.
- **C-05:** Frontend framework: Next.js 14+ (App Router) with TypeScript and Tailwind CSS.
- **C-06:** Local execution: Must run directly on developer workstation without mandatory Docker runtime during Phase 1-5 development.
- **C-07:** Anti-Agent Constraint: No LangChain, LangGraph, AutoGen, CrewAI, MCP, or autonomous looping agents in the MVP. Direct provider client SDK calls only.

### 1.5 Non-Goals for MVP
- Autonomous tool-calling agent loops.
- Fine-tuning foundation models.
- OCR parsing of handwriting, scanned tiff/jpg images, or complex OCR correction pipelines.
- Live web search or unrestricted internet browsing.
- Multi-tenant enterprise RBAC, billing, and SSO.
- High-volume asynchronous distributed task brokers (Celery/RabbitMQ) unless file volume necessitates it.

---

## 2. System Architecture and Component Responsibilities

ProofLens AI is organized as a decoupled two-tier architecture: a Next.js TypeScript frontend communicating over REST API to a FastAPI Python backend, backed by PostgreSQL 17 with `pgvector` for relational metadata and dense vector search.

```mermaid
graph TD
    subgraph Client["Frontend Client (Next.js App Router)"]
        UI_WS["Workspace & Upload View"]
        UI_QA["Q&A & Citation Panel"]
        UI_COMP["Comparison Matrix View"]
        UI_EVID["Evidence Inspector Modal"]
        UI_EVAL["Evaluation Dashboard View"]
    end

    subgraph API_Gateway["FastAPI Application Gateway"]
        Router["API Routers (/api/v1)"]
        CorsMW["CORS & Error Handlers"]
    end

    subgraph Service_Core["Modular Service Layer"]
        IngestService["Ingestion & Parsing Service<br/>(pypdf / pdfplumber)"]
        ChunkService["Chunking Engine<br/>(Recursive Character / Token Aware)"]
        EmbedService["Embedding Service<br/>(Provider Interface: OpenAI/Gemini)"]
        RetrieverService["Vector Retrieval Service<br/>(pgvector Cosine Search + Threshold)"]
        QAService["Grounded Q&A Service<br/>(Prompt Template + Abstention Policy)"]
        CiteService["Citation Validation Engine<br/>(Hallucination Gatekeeper)"]
        CompService["Cross-Doc Comparison Engine"]
        EvalService["Evaluation Runner"]
    end

    subgraph Storage_Layer["Persistence Layer"]
        LocalFS["Local File Storage<br/>(storage/uploads/)"]
        PG_DB[("PostgreSQL 17 Database<br/>(Workspaces, Docs, Chunks, Runs)")]
        PG_VEC[("pgvector Extension<br/>(Cosine Index: HNSW/IVFFlat)")]
    end

    Client -->|HTTP/JSON REST| Router
    Router --> IngestService
    Router --> RetrieverService
    Router --> QAService
    Router --> CompService
    Router --> EvalService

    IngestService --> LocalFS
    IngestService --> ChunkService
    ChunkService --> EmbedService
    EmbedService --> PG_VEC
    IngestService --> PG_DB

    RetrieverService --> EmbedService
    RetrieverService --> PG_VEC

    QAService --> RetrieverService
    QAService --> CiteService
    CiteService --> PG_DB

    CompService --> RetrieverService
    CompService --> QAService
```

### Component Responsibilities

| Component | Responsibility | Inputs / Outputs |
| :--- | :--- | :--- |
| **Ingestion Service** | Validates uploaded PDF MIME type, size, and SHA-256 hash. Saves to disk, parses pages, extracts clean text, and flags scanned/empty files. | `UploadFile` &rarr; `Document` record + list of `DocumentPage` items |
| **Chunking Engine** | Splits page text into overlapping windows (e.g. 500 chars / 100 char overlap). Enriches each chunk with `document_id`, `page_number`, and `chunk_index`. | Page text &rarr; List of `DocumentChunk` with exact provenance |
| **Embedding Service** | Abstract interface generating normalized float vector representations using batched provider API calls. | List of chunk texts &rarr; List of 1536-dim vector arrays |
| **Retrieval Engine** | Embeds queries, queries `document_chunks` using `pgvector` cosine similarity (`<=>`), applies workspace filters, and discards candidates below similarity threshold. | Query string, workspace ID, top_k &rarr; Ranked candidate chunks |
| **Grounded Q&A Service** | Formulates strictly bounded system instructions enclosing retrieved context; prompts LLM to answer using explicit citations or return `INSUFFICIENT_EVIDENCE`. | Query + Chunks &rarr; Raw answer text + claimed citations |
| **Citation Validator** | Parses claimed citations in model response, cross-checks against actual retrieved chunk IDs/page numbers, computes verification confidence, and scrubs invalid citations. | Raw answer + Retrieved chunks &rarr; Validated Answer + Verified Citations |
| **Comparison Engine** | Orchestrates multi-document retrieval on a unified topic, aligns evidence per document, and prompts LLM for side-by-side synthesis. | Topic + Document IDs &rarr; Per-document findings + agreement/contradiction matrix |
| **Evaluation Runner** | Executes deterministic benchmark queries from version-controlled JSON fixtures; evaluates retrieval recall, citation precision, and negative abstention accuracy. | Evaluation dataset &rarr; Accuracy scores, latency, failure log |

---

## 3. Main Data Flow and Workflow Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant API as FastAPI Router
    participant Ingest as Ingestion & Chunking
    participant Embed as Embedding Provider
    participant DB as Postgres + pgvector
    participant LLM as External LLM API
    participant Cite as Citation Validator

    %% INGESTION FLOW
    rect rgb(240, 248, 255)
    Note over User, DB: Document Ingestion Flow
    User->>API: POST /workspaces/{id}/documents (PDF file)
    API->>Ingest: Validate file (size, MIME, SHA-256)
    Ingest->>Ingest: Extract text per page (pypdf)
    Ingest->>Ingest: Generate chunks with page metadata
    Ingest->>Embed: Embed batch of chunks (text-embedding-3-small)
    Embed-->>Ingest: Return 1536-dim vectors
    Ingest->>DB: Insert Document & DocumentChunks with embeddings
    API-->>User: 201 Created (document_id, status: READY, chunk_count)
    end

    %% QUESTION ANSWERING FLOW
    rect rgb(245, 255, 245)
    Note over User, DB: Grounded Q&A Flow
    User->>API: POST /workspaces/{id}/query {question, document_ids?}
    API->>Embed: Embed user query
    Embed-->>API: Query vector
    API->>DB: Cosine search (pgvector: embedding <=> query_vec)
    DB-->>API: Top-K retrieved chunks with page/content metadata
    
    alt Insufficient Similarity (< threshold)
        API-->>User: 200 OK (answer: "Insufficient evidence in documents.", citations: [], status: ABSTAINED)
    else Sufficient Evidence Retrieved
        API->>LLM: Prompt with retrieved context + strict citation rules
        LLM-->>API: Generated answer with bracketed citations
        API->>Cite: Validate cited docs & pages against retrieved chunks
        Cite-->>API: Validated citations + provenance status (VERIFIED / PARTIAL / UNVERIFIED)
        API->>DB: Record QueryRun, Answer, and Citations
        API-->>User: 200 OK (answer, validated_citations, retrieved_passages)
    end
    end
```

---

## 4. Backend Folder Structure, Module Boundaries, and Dependency Rules

### 4.1 Folder Structure
```
backend/
├── alembic/                      # Database migrations
│   ├── versions/                 # Versioned migration scripts
│   └── env.py                    # Alembic migration environment
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI application factory & lifespan
│   ├── core/                     # Application configuration & cross-cutting concerns
│   │   ├── __init__.py
│   │   ├── config.py             # Pydantic BaseSettings (env vars)
│   │   ├── database.py           # SQLAlchemy async engine & session maker
│   │   ├── exceptions.py         # Custom application exceptions
│   │   ├── logging.py            # Structured logging configuration
│   │   └── security.py           # File validation, path sanitization, rate limiting
│   ├── models/                   # SQLAlchemy ORM declarative models
│   │   ├── __init__.py
│   │   ├── workspace.py          # Workspace ORM model
│   │   ├── document.py           # Document & DocumentPage ORM models
│   │   ├── chunk.py              # DocumentChunk ORM model (pgvector column)
│   │   ├── query.py              # QueryRun, Answer, Citation ORM models
│   │   ├── comparison.py         # ComparisonRun ORM model
│   │   └── evaluation.py         # EvaluationCase & EvaluationRun ORM models
│   ├── schemas/                  # Pydantic v2 validation & response DTOs
│   │   ├── __init__.py
│   │   ├── workspace.py          # WorkspaceCreate, WorkspaceResponse
│   │   ├── document.py           # DocumentResponse, IngestStatusResponse
│   │   ├── query.py              # QueryRequest, QueryResponse, CitationDTO
│   │   ├── comparison.py         # ComparisonRequest, ComparisonResponse
│   │   └── evaluation.py         # EvaluationReportResponse
│   ├── services/                 # Pure domain business logic (no HTTP logic)
│   │   ├── __init__.py
│   │   ├── document_service.py   # PDF storage, extraction, validation
│   │   ├── chunking_service.py   # Token/character sliding window chunking
│   │   ├── embedding_service.py  # Provider interface & implementation
│   │   ├── retrieval_service.py  # Vector search & relevance scoring
│   │   ├── qa_service.py         # Grounded prompt synthesis & LLM call
│   │   ├── citation_service.py   # Citation parsing & proof validation
│   │   ├── comparison_service.py # Multi-document comparative analysis
│   │   └── evaluation_service.py # Evaluation test suite harness
│   └── api/                      # FastAPI endpoint routing
│       ├── __init__.py
│       ├── deps.py               # Dependency injection (DB session, services)
│       └── v1/
│           ├── __init__.py
│           ├── router.py         # Aggregated v1 APIRouter
│           ├── health.py         # /health & /ready endpoints
│           ├── workspaces.py     # /workspaces CRUD
│           ├── documents.py      # /workspaces/{id}/documents (upload/delete/list)
│           ├── queries.py        # /workspaces/{id}/query
│           ├── comparisons.py    # /workspaces/{id}/compare
│           └── evaluations.py    # /evaluations/run
├── storage/                      # Local uploaded PDF binary files (git-ignored)
│   └── uploads/
├── tests/                        # Automated tests (pytest)
│   ├── conftest.py               # Test DB fixture, mock LLM client
│   ├── unit/                     # Unit tests (chunking, citation parser, abstention)
│   ├── integration/              # Integration tests (FastAPI TestClient + DB)
│   └── fixtures/                 # Sample PDFs & evaluation JSON datasets
├── alembic.ini                   # Alembic configuration
├── pyproject.toml / requirements.txt # Python dependencies
└── .env.example                  # Documented environment template
```

### 4.2 Module Boundaries and Dependency Rules
1. **Unidirectional Dependency Flow:** `api` &rarr; `services` &rarr; `models`/`schemas` &larr; `core`.
2. **HTTP Agnostic Services:** Modules in `app/services/` must NEVER import `FastAPI`, `Request`, `Response`, or `HTTPException`. Services raise domain exceptions defined in `app/core/exceptions.py`.
3. **API Layer Exception Mapping:** The `api` router or a global exception handler translates domain exceptions into standard RFC 7807 problem details or uniform JSON error responses.
4. **Provider Isolation:** LLM and Embedding API clients are hidden behind domain protocols in `app/services/embedding_service.py` and `app/services/qa_service.py`. No external provider types (e.g. `openai.types`) bleed into database models or API routes.

---

## 5. Frontend Folder Structure, Routes, Components, and Responsibilities

### 5.1 Next.js 14 App Router Structure
```
frontend/
├── public/                       # Static assets, icons, logos
├── src/
│   ├── app/                      # Next.js App Router
│   │   ├── layout.tsx            # Global layout (Navigation, Theme, Providers)
│   │   ├── page.tsx              # Workspace dashboard / selection
│   │   ├── workspaces/
│   │   │   └── [workspaceId]/
│   │   │       ├── page.tsx      # Main Document Intelligence Workspace (Q&A + Library)
│   │   │       ├── compare/
│   │   │       │   └── page.tsx  # Cross-Document Comparison View
│   │   │       └── evaluation/
│   │   │           └── page.tsx  # Evaluation Benchmark & Quality Reports
│   ├── components/               # Modular UI components
│   │   ├── common/               # Core atomic primitives (Button, Modal, Badge, Spinner)
│   │   ├── documents/            # DocumentUploadDropzone, DocumentList, IngestStatusBadge
│   │   ├── qa/                   # QueryInput, AnswerCard, CitationPill, AbstentionAlert
│   │   ├── evidence/             # EvidenceDrawer, PassageViewer, PageHighlight
│   │   ├── comparison/           # DocumentSelector, ComparisonMatrix, FindingCard
│   │   └── evaluation/           # MetricScorecard, TestCaseTable, RunEvaluationButton
│   ├── hooks/                    # Reusable React hooks
│   │   ├── useWorkspace.ts       # Workspace state & active documents
│   │   ├── useDocuments.ts       # Upload & ingestion polling
│   │   ├── useQuery.ts           # Grounded Q&A execution
│   │   └── useComparison.ts      # Multi-doc comparison state
│   ├── lib/                      # Utilities & API client
│   │   ├── api-client.ts         # Type-safe Fetch wrapper with error handling
│   │   ├── endpoints.ts          # API route URL builders
│   │   └── utils.ts              # Classnames, formatters, byte/date formatters
│   └── types/                    # Shared TypeScript interfaces
│       ├── api.ts                # API request/response payloads (mirrors backend schemas)
│       └── domain.ts             # Workspace, Document, Chunk, Citation, Answer
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.mjs
```

### 5.2 Key Views & Component Responsibilities
- **Workspace Dashboard (`/workspaces/[id]`):** Split-pane layout. Left pane: Document library with live upload dropzone and ingestion badges (`PROCESSING`, `READY`, `ERROR`). Right pane: Conversation-style grounded inquiry interface.
- **Evidence Drawer Component:** Sliding drawer displaying full passage excerpt, source document title, page number, and similarity score when a user clicks a citation pill.
- **Comparison Matrix View (`/workspaces/[id]/compare`):** Multi-select document picker and topic input. Renders a side-by-side tabular comparison with per-document evidence excerpts and consensus flags (`AGREEMENT`, `DIFFERENCE`, `INCOMPARABLE`).
- **Evaluation Dashboard (`/workspaces/[id]/evaluation`):** Displays retrieval hit rate (e.g. 92%), citation validity percentage (100%), and negative query abstention rate with detailed test run history.

---

## 6. Database Schema Design

The schema uses PostgreSQL 17 with the `pgvector` extension enabled.

```mermaid
erDiagram
    WORKSPACES ||--o{ DOCUMENTS : contains
    DOCUMENTS ||--o{ DOCUMENT_PAGES : has
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : splits_into
    WORKSPACES ||--o{ QUERY_RUNS : executes
    QUERY_RUNS ||--|| ANSWERS : produces
    QUERY_RUNS ||--o{ RETRIEVED_EVIDENCE : retrieves
    ANSWERS ||--o{ CITATIONS : references
    DOCUMENT_CHUNKS ||--o{ RETRIEVED_EVIDENCE : matches
    DOCUMENT_CHUNKS ||--o{ CITATIONS : grounds
    WORKSPACES ||--o{ COMPARISON_RUNS : initiates
    WORKSPACES ||--o{ EVALUATION_RUNS : assesses

    WORKSPACES {
        uuid id PK
        varchar title
        text description
        timestamp created_at
        timestamp updated_at
    }

    DOCUMENTS {
        uuid id PK
        uuid workspace_id FK
        varchar filename
        varchar file_path
        varchar file_hash_sha256
        integer file_size_bytes
        integer total_pages
        varchar status
        text error_message
        timestamp created_at
        timestamp updated_at
    }

    DOCUMENT_PAGES {
        uuid id PK
        uuid document_id FK
        integer page_number
        text raw_text
        integer character_count
        timestamp created_at
    }

    DOCUMENT_CHUNKS {
        uuid id PK
        uuid document_id FK
        uuid workspace_id FK
        integer page_number
        integer chunk_index
        text content
        integer token_count
        vector embedding_1536
        timestamp created_at
    }

    QUERY_RUNS {
        uuid id PK
        uuid workspace_id FK
        text question
        jsonb selected_document_ids
        float similarity_threshold
        integer top_k
        integer execution_time_ms
        timestamp created_at
    }

    ANSWERS {
        uuid id PK
        uuid query_run_id FK
        text answer_text
        varchar status
        boolean is_abstained
        text abstention_reason
        timestamp created_at
    }

    RETRIEVED_EVIDENCE {
        uuid id PK
        uuid query_run_id FK
        uuid chunk_id FK
        float similarity_score
        integer rank
        timestamp created_at
    }

    CITATIONS {
        uuid id PK
        uuid answer_id FK
        uuid chunk_id FK
        uuid document_id FK
        integer page_number
        text cited_excerpt
        varchar verification_status
        timestamp created_at
    }

    COMPARISON_RUNS {
        uuid id PK
        uuid workspace_id FK
        text topic
        jsonb document_ids
        jsonb comparison_matrix
        timestamp created_at
    }

    EVALUATION_RUNS {
        uuid id PK
        uuid workspace_id FK
        varchar suite_name
        integer total_cases
        integer passed_cases
        float retrieval_hit_rate
        float citation_validity_rate
        float abstention_accuracy
        jsonb raw_results
        timestamp created_at
    }
```

### Table Definitions & Vector Dimensions

1. **`workspaces`**
   - `id`: UUID (PK, default `gen_random_uuid()`)
   - `title`: VARCHAR(255) NOT NULL
   - `description`: TEXT NULL
   - `created_at`, `updated_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()

2. **`documents`**
   - `id`: UUID (PK)
   - `workspace_id`: UUID (FK &rarr; `workspaces.id` ON DELETE CASCADE, NOT NULL)
   - `filename`: VARCHAR(255) NOT NULL
   - `file_path`: VARCHAR(512) NOT NULL
   - `file_hash_sha256`: CHAR(64) NOT NULL
   - `file_size_bytes`: INTEGER NOT NULL
   - `total_pages`: INTEGER NOT NULL DEFAULT 0
   - `status`: VARCHAR(32) NOT NULL DEFAULT 'PENDING' (`PENDING`, `PARSING`, `INDEXING`, `READY`, `FAILED`, `UNSUPPORTED`)
   - `error_message`: TEXT NULL
   - `created_at`, `updated_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()
   - *Indexes:* `idx_documents_workspace_id`, `idx_documents_hash_workspace (workspace_id, file_hash_sha256)`

3. **`document_pages`**
   - `id`: UUID (PK)
   - `document_id`: UUID (FK &rarr; `documents.id` ON DELETE CASCADE, NOT NULL)
   - `page_number`: INTEGER NOT NULL (1-indexed)
   - `raw_text`: TEXT NOT NULL
   - `character_count`: INTEGER NOT NULL
   - `created_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()
   - *Indexes:* `idx_doc_pages_doc_page (document_id, page_number)` UNIQUE

4. **`document_chunks`**
   - `id`: UUID (PK)
   - `document_id`: UUID (FK &rarr; `documents.id` ON DELETE CASCADE, NOT NULL)
   - `workspace_id`: UUID (FK &rarr; `workspaces.id` ON DELETE CASCADE, NOT NULL)
   - `page_number`: INTEGER NOT NULL
   - `chunk_index`: INTEGER NOT NULL
   - `content`: TEXT NOT NULL
   - `token_count`: INTEGER NOT NULL
   - `embedding`: `vector(1536)` NOT NULL  *(dimension matched to OpenAI `text-embedding-3-small`)*
   - `created_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()
   - *Indexes:* 
     - `idx_chunks_workspace_id (workspace_id)`
     - `idx_chunks_doc_page (document_id, page_number)`
     - `idx_chunks_embedding_cosine`: HNSW or IVFFlat index using `vector_cosine_ops`:
       ```sql
       CREATE INDEX idx_chunks_embedding_hnsw ON document_chunks 
       USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
       ```

5. **`query_runs`**
   - `id`: UUID (PK)
   - `workspace_id`: UUID (FK &rarr; `workspaces.id` ON DELETE CASCADE, NOT NULL)
   - `question`: TEXT NOT NULL
   - `selected_document_ids`: JSONB NULL  *(optional document filter)*
   - `similarity_threshold`: FLOAT NOT NULL DEFAULT 0.65
   - `top_k`: INTEGER NOT NULL DEFAULT 5
   - `execution_time_ms`: INTEGER NULL
   - `created_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()

6. **`answers`**
   - `id`: UUID (PK)
   - `query_run_id`: UUID (FK &rarr; `query_runs.id` ON DELETE CASCADE, NOT NULL UNIQUE)
   - `answer_text`: TEXT NOT NULL
   - `status`: VARCHAR(32) NOT NULL DEFAULT 'SUCCESS' (`SUCCESS`, `ABSTAINED`, `FAILED`)
   - `is_abstained`: BOOLEAN NOT NULL DEFAULT FALSE
   - `abstention_reason`: TEXT NULL
   - `created_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()

7. **`citations`**
   - `id`: UUID (PK)
   - `answer_id`: UUID (FK &rarr; `answers.id` ON DELETE CASCADE, NOT NULL)
   - `chunk_id`: UUID (FK &rarr; `document_chunks.id` ON DELETE CASCADE, NOT NULL)
   - `document_id`: UUID (FK &rarr; `documents.id` ON DELETE CASCADE, NOT NULL)
   - `page_number`: INTEGER NOT NULL
   - `cited_excerpt`: TEXT NOT NULL
   - `verification_status`: VARCHAR(32) NOT NULL DEFAULT 'VERIFIED' (`VERIFIED`, `PARTIAL`, `UNVERIFIED`)
   - `created_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()

8. **`comparison_runs`**
   - `id`: UUID (PK)
   - `workspace_id`: UUID (FK &rarr; `workspaces.id` ON DELETE CASCADE, NOT NULL)
   - `topic`: TEXT NOT NULL
   - `document_ids`: JSONB NOT NULL
   - `comparison_matrix`: JSONB NOT NULL
   - `created_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()

9. **`evaluation_runs`**
   - `id`: UUID (PK)
   - `workspace_id`: UUID (FK &rarr; `workspaces.id` ON DELETE CASCADE, NOT NULL)
   - `suite_name`: VARCHAR(128) NOT NULL
   - `total_cases`: INTEGER NOT NULL
   - `passed_cases`: INTEGER NOT NULL
   - `retrieval_hit_rate`: FLOAT NOT NULL
   - `citation_validity_rate`: FLOAT NOT NULL
   - `abstention_accuracy`: FLOAT NOT NULL
   - `raw_results`: JSONB NOT NULL
   - `created_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()

---

## 7. Alembic Migration Strategy

1. **Initial Vector Extension Migration (`001_enable_pgvector.py`):**
   ```python
   def upgrade():
       op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
   def downgrade():
       op.execute("DROP EXTENSION IF EXISTS vector;")
   ```
2. **Schema Baseline Migration (`002_create_initial_schema.py`):**
   Creates all relational tables, foreign key cascades, unique constraints, and standard btree indexes.
3. **Vector Index Migration (`003_add_hnsw_vector_index.py`):**
   Builds the HNSW cosine index on `document_chunks.embedding`.
4. **Handling Embedding Model Changes (Dimensionality Migration Strategy):**
   If the embedding model changes (e.g. from 1536-dim to 768-dim):
   - Chunks must be re-embedded; vector dimensions cannot simply be cast in-place.
   - The migration strategy adds a new column (e.g., `embedding_new vector(768)`), updates configuration, triggers a backfill CLI command, swaps the columns, and drops the deprecated vector column.

---

## 8. API Endpoints Specification

Base Path: `/api/v1`

### 8.1 Workspaces
- **`POST /api/v1/workspaces`**
  - *Request:* `{"title": "Research Seminar", "description": "Optional notes"}`
  - *Response (201 Created):* `{"id": "uuid", "title": "...", "created_at": "..."}`
  - *Errors:* `422 Unprocessable Entity` (validation failure)
- **`GET /api/v1/workspaces`**
  - *Response (200 OK):* List of workspace summaries.
- **`GET /api/v1/workspaces/{workspace_id}`**
  - *Response (200 OK):* Workspace details with attached documents summary.
  - *Errors:* `404 Not Found`

### 8.2 Documents
- **`POST /api/v1/workspaces/{workspace_id}/documents`**
  - *Request:* `multipart/form-data` with `file: UploadFile` (PDF)
  - *Validation:* MIME `application/pdf`, max size 10MB, non-empty, digital text check.
  - *Response (201 Created):* 
    ```json
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "workspace_id": "...",
      "filename": "q3_report.pdf",
      "file_size_bytes": 1048576,
      "total_pages": 12,
      "status": "READY",
      "chunk_count": 48
    }
    ```
  - *Errors:* `400 Bad Request` (not a valid PDF / scanned image), `409 Conflict` (duplicate file hash in workspace), `413 Payload Too Large` (> 10MB)
- **`GET /api/v1/workspaces/{workspace_id}/documents`**
  - *Response (200 OK):* List of documents with current ingestion status.
- **`DELETE /api/v1/workspaces/{workspace_id}/documents/{document_id}`**
  - *Response (204 No Content):* Deletes document record, associated pages, chunks, embeddings, and deletes local PDF binary.
  - *Errors:* `404 Not Found`

### 8.3 Grounded Q&A
- **`POST /api/v1/workspaces/{workspace_id}/query`**
  - *Request:*
    ```json
    {
      "question": "What was the reported operating revenue in Q3?",
      "document_ids": ["optional-filter-uuid"],
      "similarity_threshold": 0.65,
      "top_k": 5
    }
    ```
  - *Response (200 OK):*
    ```json
    {
      "query_run_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "question": "What was the reported operating revenue in Q3?",
      "answer": "Operating revenue for Q3 reached $14.2M, representing a 12% YoY increase [Doc: q3_report.pdf, Page: 4].",
      "is_abstained": false,
      "abstention_reason": null,
      "citations": [
        {
          "citation_id": "c1a2b3c4-...",
          "document_id": "3fa85f64-...",
          "document_name": "q3_report.pdf",
          "page_number": 4,
          "excerpt": "Operating revenue for the third quarter ended September 30 was $14.2 million...",
          "verification_status": "VERIFIED"
        }
      ],
      "retrieved_evidence": [
        {
          "chunk_id": "e5f6...",
          "document_id": "3fa85f64-...",
          "document_name": "q3_report.pdf",
          "page_number": 4,
          "similarity_score": 0.88,
          "content": "..."
        }
      ]
    }
    ```
  - *Abstention Response (200 OK):*
    ```json
    {
      "query_run_id": "...",
      "question": "What is the warranty policy on hardware?",
      "answer": "The available documents do not contain sufficient evidence to answer this question.",
      "is_abstained": true,
      "abstention_reason": "No retrieved passages met the minimum relevance threshold of 0.65.",
      "citations": [],
      "retrieved_evidence": []
    }
    ```

### 8.4 Cross-Document Comparison
- **`POST /api/v1/workspaces/{workspace_id}/compare`**
  - *Request:*
    ```json
    {
      "topic": "Net profit margin expectations for fiscal year 2026",
      "document_ids": ["doc-uuid-1", "doc-uuid-2"]
    }
    ```
  - *Response (200 OK):*
    ```json
    {
      "comparison_run_id": "...",
      "topic": "Net profit margin expectations...",
      "documents_analyzed": ["doc-uuid-1", "doc-uuid-2"],
      "findings": [
        {
          "document_id": "doc-uuid-1",
          "document_name": "annual_outlook.pdf",
          "summary": "Projects net margin between 18% and 21%.",
          "citations": [{"page_number": 14, "excerpt": "..."}]
        },
        {
          "document_id": "doc-uuid-2",
          "document_name": "analyst_brief.pdf",
          "summary": "Estimates conservative net margin of 15% due to tariff pressures.",
          "citations": [{"page_number": 3, "excerpt": "..."}]
        }
      ],
      "synthesis": {
        "consensus": "DIFFERENCE",
        "analysis": "The documents present conflicting margin expectations: annual_outlook anticipates 18-21% while analyst_brief anticipates 15%."
      }
    }
    ```

### 8.5 Evaluation
- **`POST /api/v1/workspaces/{workspace_id}/evaluations/run`**
  - *Request:* `{"test_suite": "standard_benchmark_v1"}`
  - *Response (200 OK):* Evaluation scorecard with hit rate, citation validity rate, abstention precision, and detailed failure log.

---

## 9. PDF Upload, Page-Aware Extraction, Chunking & Provenance

### 9.1 PDF Ingestion & Validation
1. **Size Gate:** Maximum 10MB per file.
2. **Format Gate:** Validates magic bytes `%PDF` and MIME `application/pdf`.
3. **Integrity & Duplication:** Computes SHA-256 hash. Rejects duplicate uploads within the same workspace to prevent redundant vectors.
4. **Scanned PDF Check:** Uses `pypdf` to inspect character yields across pages. If average text per page is `< 40` characters across a multi-page document, the document is rejected with `UNSUPPORTED_SCANNED_PDF` rather than silently indexing empty strings.

### 9.2 Provenance-Preserving Extraction
- Extraction iterates sequentially over `reader.pages`.
- Each page is assigned its 1-indexed physical page number `page_number = i + 1`.
- Raw text is normalized (whitespace collapsed, null bytes removed, hyphens re-joined across line breaks).
- Clean text is persisted to `document_pages` before chunking. This enables the Evidence Inspector to highlight passages within the context of the entire page.

### 9.3 Sliding Window Chunking Strategy
- **Chunk Size:** 500 characters (approx. 100-120 tokens).
- **Chunk Overlap:** 100 characters.
- **Boundary Splitting:** Recursive separator precedence: `\n\n` &rarr; `\n` &rarr; `. ` &rarr; ` ` &rarr; character split.
- **Page Isolation:** Chunks NEVER span across page boundaries. A chunk belongs strictly to a single page. This guarantees that every citation points unequivocally to an exact, uncompromised page number.
- **Chunk Metadata Tuple:** Every chunk stores `(workspace_id, document_id, page_number, chunk_index, token_count)`.

---

## 10. Embedding Generation, Vector Storage & Retrieval

### 10.1 Embedding Generation
- **Default Provider:** OpenAI `text-embedding-3-small`.
- **Dimensions:** 1536 floating-point values.
- **Normalization:** Vectors are L2-normalized upon generation to enable efficient cosine distance calculations.
- **Batching:** Chunks are embedded in batches of up to 100 items with exponential backoff on HTTP 429 rate limits.

### 10.2 Vector Storage in PostgreSQL (`pgvector`)
- Column type: `vector(1536)` on `document_chunks`.
- Index: HNSW index using cosine distance operator (`vector_cosine_ops`).
- Cosine Distance Formula:
  $$\text{Cosine Similarity} = 1 - (\text{embedding} \Leftrightarrow \text{query\_vector})$$

### 10.3 Retrieval & Ranking Workflow
1. User question is embedded using the identical embedding model.
2. Filtered query executed against `document_chunks`:
   ```sql
   SELECT id, document_id, page_number, chunk_index, content,
          1 - (embedding <=> :query_vector) AS similarity_score
   FROM document_chunks
   WHERE workspace_id = :workspace_id
     AND (:document_ids IS NULL OR document_id = ANY(:document_ids))
     AND (1 - (embedding <=> :query_vector)) >= :similarity_threshold
   ORDER BY embedding <=> :query_vector ASC
   LIMIT :top_k;
   ```
3. If no chunks exceed `similarity_threshold` (default 0.65), the retrieval service signals `ZERO_EVIDENCE`, triggering immediate abstention without invoking the generative LLM.

---

## 11. Evidence-Grounded Answers, Citation Validation & Abstention

### 11.1 Prompt Design (Grounding Guardrail)
System prompt strictly limits the LLM's epistemic boundary:
```text
You are ProofLens AI, an evidence-grounded document analysis engine.
Answer the user's question ONLY using the factual statements in the provided Retrieved Context below.

RULES:
1. Every factual statement in your answer MUST cite its source using this format: [Doc: <doc_name>, Page: <page_num>].
2. NEVER use prior knowledge or external assumptions.
3. If the Retrieved Context does not explicitly contain enough information to answer the question, state exactly:
   "The available documents do not contain sufficient evidence to answer this question."
4. Do NOT speculate, extrapolate, or invent document titles or page numbers.

--- RETRIEVED CONTEXT ---
[Doc: {doc_name}, Page: {page_num}, ChunkID: {chunk_id}]
{chunk_content}
-------------------------
```

### 11.2 Server-Side Citation Validation Pipeline
To ensure verifiable citations and eliminate AI hallucinations:
1. **Citation Parsing:** Server parses all `[Doc: ..., Page: ...]` markers from the LLM output via regular expression.
2. **Provenance Cross-Check:** For each parsed citation, the server checks if a retrieved chunk matches both the referenced `document_name` and `page_number`.
3. **Content Verification:** The server verifies that key phrases in the sentence preceding the citation share lexical overlap with the matched chunk.
4. **Sanitization:**
   - If a citation matches retrieved chunks &rarr; marked `VERIFIED`.
   - If a citation references a document/page NOT present in the retrieved set &rarr; stripped from output and logged as a hallucination attempt.
5. **Post-Validation Abstention Gate:** If 100% of the model's citations fail verification, the answer status is reverted to `ABSTAINED` with reason `"Generated citations could not be verified against source evidence."`

---

## 12. Cross-Document Comparison and Evaluation Strategy

### 12.1 Cross-Document Comparison Logic
1. User provides a topic (e.g. "Cloud migration timeline") and selects $\ge 2$ documents.
2. Retrieval executes scoped queries per document to retrieve top relevant chunks for each document individually.
3. LLM is prompted with partitioned context blocks (`=== Document A: [title] ===`, `=== Document B: [title] ===`).
4. Output is required in a structured JSON schema:
   - `findings`: array of objects containing `document_id`, `statement`, and `citation`.
   - `consensus`: enum (`AGREEMENT`, `DIFFERENCE`, `CONTRADICTION`, `INCOMPARABLE_SCOPES`).
   - `synthesis_notes`: explanation of differences or missing coverage.

### 12.2 Automated Evaluation Suite
The evaluation engine runs headless via CLI (`pytest tests/evaluation/` or `python -m app.services.evaluation_service`):
- **Test Dataset:** Version-controlled JSON fixture (`tests/fixtures/eval_dataset_v1.json`) containing:
  - 10 Positive Cases: Question, target document, expected target page, golden keywords.
  - 5 Negative Cases: Questions completely unanswerable from the test corpus.
  - 3 Comparative Cases: Known discrepancies between two test documents.
- **Automated Metrics Calculated:**
  - **Retrieval Hit Rate:** $\%$ of positive cases where the true source page was in Top-5 retrieved chunks. Target: $\ge 85\%$.
  - **Citation Validity Rate:** $\%$ of output citations that map directly to true retrieved passages. Target: $100\%$.
  - **Abstention Accuracy:** $\%$ of negative cases where system successfully abstained. Target: $100\%$.
  - **Evaluation Transparency:** All metrics explicitly state whether they are deterministic code checks or model-assisted reviews.

---

## 13. Configuration, Secrets, Logging, Error Handling & Security

### 13.1 Configuration & Environment Variables (`.env`)
```bash
# Application
ENVIRONMENT=development
DEBUG=true
PORT=8000
HOST=127.0.0.1
CORS_ORIGINS=["http://localhost:3000"]

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/prooflens_db
DB_ECHO=false

# Storage
STORAGE_DIR=storage/uploads
MAX_UPLOAD_SIZE_BYTES=10485760  # 10MB

# AI Provider Settings
LLM_PROVIDER=openai             # openai | gemini | local
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
SIMILARITY_THRESHOLD_DEFAULT=0.65
TOP_K_DEFAULT=5
```

### 13.2 Security Guardrails
1. **Zero Secret Leakage:** `.env` is strictly git-ignored; settings loaded via Pydantic `BaseSettings`. API keys are never passed to the frontend.
2. **File Path Traversal Defense:** Uploaded files are renamed on disk to UUIDs (`storage/uploads/{doc_uuid}.pdf`). Original filenames are stored only as database metadata.
3. **Indirect Prompt Injection Defense:** All retrieved document text injected into prompts is enclosed within strict XML/Markdown delimiters. System instructions specify that document text has zero administrative authority and cannot issue commands to the model.
4. **Structured Error Handling:** Production error responses follow a uniform JSON structure:
   ```json
   {
     "error_code": "DOCUMENT_NOT_FOUND",
     "message": "Document with id ... does not exist in workspace ...",
     "details": null
   }
   ```
   No Python tracebacks or database connection strings are exposed in API responses.

---

## 14. Testing Strategy

### 14.1 Backend Testing (pytest)
- **Unit Tests:**
  - `test_chunking.py`: Verifies recursive splitting, character overlap, and that chunks do not cross page boundaries.
  - `test_citation_service.py`: Tests regex citation parser, valid match verification, and scrubbing of hallucinated citations.
  - `test_abstention.py`: Tests that low similarity scores correctly bypass generation and trigger structured abstention.
- **Integration Tests:**
  - `test_document_ingestion.py`: Uploads a mock multi-page PDF, verifies extraction, vector persistence, and database cascade deletions.
  - `test_query_flow.py`: Executes end-to-end query flow with a mocked LLM client returning verified citations.
- **Fixtures:**
  - Pre-generated 3-page synthetic PDF fixture (`sample_report.pdf`).
  - Mocked OpenAI client fixture returning deterministic vectors and structured responses for offline testing.

### 14.2 Frontend Testing
- **Tooling:** Vitest + React Testing Library (lightweight, zero-config with Next.js, 10x faster than Jest).
- **Coverage Focus:**
  - `CitationPill.test.tsx`: Clicking pill opens the Evidence Drawer with correct page and excerpt.
  - `AbstentionAlert.test.tsx`: Renders abstention styling when `is_abstained: true`.
  - `DocumentUploadDropzone.test.tsx`: Validates client-side file size and rejects non-PDF files.

---

## 15. Local Development Setup & Future Docker Strategy

### 15.1 Local Development (Non-Docker, Native Windows)
1. **PostgreSQL 17 Setup:**
   - PostgreSQL 17 is already installed and running as a Windows service on the local machine (`postgresql-x64-17`).
   - Create local database:
     ```powershell
     psql -U postgres -c "CREATE DATABASE prooflens_db;"
     psql -U postgres -d prooflens_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
     ```
2. **Backend Setup:**
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   ```
3. **Frontend Setup:**
   ```powershell
   cd frontend
   npm.cmd install
   npm.cmd run dev
   ```

### 15.2 Future Docker Production Strategy (Deferred Phase)
- `docker-compose.yml` comprising:
  - `prooflens-db`: `pgvector/pgvector:pg17` image.
  - `prooflens-backend`: Multi-stage Python 3.13 slim image.
  - `prooflens-frontend`: Next.js standalone output image.
  - Reverse proxy / Nginx or Traefik routing.

---

## 16. Important Design Decisions, Alternatives Considered & Unresolved Questions

### 16.1 Key Architectural Decisions & Alternatives

| Decision | Selected Choice | Alternatives Considered | Rationale |
| :--- | :--- | :--- | :--- |
| **Vector Database** | PostgreSQL 17 + `pgvector` | ChromaDB, Pinecone, Qdrant | Keeps metadata, document text, and vector embeddings in a single ACID-compliant database. Eliminates distributed synchronization issues. |
| **Orchestration Framework** | Native Python / Direct SDK calls | LangChain, LlamaIndex, LangGraph | Minimizes dependency bloat, provides 100% control over prompts and citation verification, and prevents leaky framework abstractions. |
| **PDF Extraction Library** | `pypdf` + `pdfplumber` fallback | PyMuPDF (fitz), Tesseract OCR | Pure-python / lightweight, reliable page-by-page text stream isolation without complex C++ binary build requirements on Windows. |
| **Citation Verification** | Dual-phase (Prompt-enforced + Server-side regex validation) | Unverified LLM generation | Raw LLM citations suffer from hallucinated page numbers. Server-side validation guarantees zero false citations reach the UI. |

### 16.2 Unresolved Questions for Project Owner Approval
1. **Default AI Model Provider:** Does the project owner prefer **OpenAI** (`gpt-4o-mini` + `text-embedding-3-small`) or **Google Gemini** (`gemini-1.5-flash` + `text-embedding-004`) for the initial API keys?
2. **Local PostgreSQL Credentials:** What credentials should the default `.env.example` specify for PostgreSQL (e.g. `postgres:postgres@localhost:5432/prooflens_db`)?
3. **Evaluation Dataset Domain:** For the college demonstration test set, what domain of sample PDFs is preferred (e.g. financial earnings reports, AI research papers, or university course syllabi)?
