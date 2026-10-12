# ProofLens AI — Phase 0: Technical Design and Implementation Planning

We are starting ProofLens AI from scratch in an empty project folder.

## Step 1: Read and verify the PRD

Locate and read `ProofLens-AI-Project-Kickoff-PRD-v0.1.md` completely before making any changes.

- Read the entire document, including requirements, constraints, workflows, acceptance criteria, and non-functional requirements.
- Treat the PRD as the source of truth.
- If the PRD is missing, inaccessible, or incomplete, stop and ask me to provide it. Do not invent its contents.
- Identify ambiguities, assumptions, and unresolved decisions. Document them explicitly.
- Do not add features outside the PRD unless clearly marked as optional future enhancements.

## Step 2: Project constraints

This is a new project in an empty folder, not an existing application to refactor.

Use this proposed stack:

- Backend: Python and FastAPI
- Database: PostgreSQL with pgvector
- Frontend: Next.js with TypeScript
- AI: External LLM API and embedding API
- Database migrations: Alembic
- Backend testing: pytest
- Frontend testing: Choose suitable lightweight tools and justify the choice
- Local development: Run services locally without requiring Docker
- Production: Plan a Docker-based strategy for a later phase

Keep the MVP focused on the PRD. Do not introduce AI agents, LangGraph, MCP, multi-agent orchestration, microservices, Kubernetes, or unnecessary infrastructure.

Make explicit recommendations for open technical decisions. Prefer simple, maintainable solutions.

## Step 3: Create the Technical Design Document

Create `docs/TECHNICAL-DESIGN.md`.

Include:

1. Project goals, scope, assumptions, constraints, and non-goals.
2. System architecture, component responsibilities, and a Mermaid architecture diagram.
3. Main data flow and a Mermaid workflow diagram.
4. Backend folder structure, module boundaries, and dependency rules.
5. Frontend folder structure, routes, components, and responsibilities.
6. Database schema: tables, columns, data types, primary keys, foreign keys, relationships, indexes, vector dimensions, and constraints.
7. Alembic migration strategy, including schema changes and embedding-model changes.
8. API endpoints with HTTP methods, request schemas, response schemas, status codes, and error responses.
9. PDF upload validation, page-aware text extraction, chunking, metadata, and provenance preservation.
10. Embedding generation, vector storage, retrieval, ranking, and RAG workflow.
11. Evidence-grounded answers, citation validation, and insufficient-evidence abstention.
12. Cross-document comparison and evaluation requirements specified by the PRD.
13. Configuration, environment variables, secrets management, logging, error handling, and security.
14. Unit, integration, and AI evaluation testing strategy.
15. Local development setup, external services, and future Docker/production strategy.
16. Important design decisions, alternatives considered, assumptions, and unresolved questions.

Ensure the architecture, schema, endpoints, and workflows are consistent with each other.

## Step 4: Create the phased implementation plan

Create `docs/IMPLEMENTATION-PLAN.md`.

Organize the work into small, ordered phases with dependencies and clear completion criteria.

For every phase include:

- Objective and scope
- Prerequisites and dependencies
- Tasks and expected deliverables
- Files or modules expected to be created during that future phase
- Tests and verification steps
- Explicit, measurable acceptance criteria
- Definition of Done
- Risks and relevant decisions
- Git commit/push checkpoint, to be performed only when implementation is later authorized

Cover the PRD requirements in the appropriate order: foundation, ingestion, retrieval, grounded Q&A, citations, comparison, and evaluation.

Separate essential MVP work from optional future enhancements. Optional enhancements must not become prerequisites for the MVP.

## Step 5: Strict execution restrictions

This is a documentation-only planning phase.

You are authorized to create or edit only these two files:

- `docs/TECHNICAL-DESIGN.md`
- `docs/IMPLEMENTATION-PLAN.md`

You must NOT:

- Create application code or scaffolding.
- Create package manifests or dependency files.
- Install packages or run package managers.
- Initialize Git or create commits.
- Configure external services or API keys.
- Create database instances or run migrations.
- Deploy the application.
- Modify or overwrite the PRD.
- Create additional documentation files.

Creating the `docs/` directory is allowed if it does not exist.

## Step 6: Quality review before stopping

Before finishing:

1. Verify that both requested documents exist and contain substantive content.
2. Cross-check the documents against the PRD requirements.
3. Check consistency between architecture, database schema, API contracts, workflows, and implementation phases.
4. Identify requirements that are ambiguous or need my approval.
5. List assumptions explicitly. Never claim an assumption came from the PRD.
6. Confirm that no application code, dependencies, Git repository, or deployment was created.

## Step 7: Mandatory phase approval gate

Follow a strict approval-based workflow throughout the project.

- Complete only the currently authorized phase.
- At the end of each phase, stop and present a concise phase report: what was completed, files changed, tests/verification performed, acceptance criteria met or unmet, known issues, and the proposed next phase.
- Ask me explicitly for permission to begin the next phase.
- Do not start the next phase, make changes belonging to it, or assume approval from silence or a general earlier instruction.
- Wait until I clearly approve the next phase before proceeding.
- If acceptance criteria are not met, explain what remains and ask how I want to proceed. Do not mark the phase complete inaccurately.
- This approval gate applies even if the next phase seems straightforward or is listed in the implementation plan.

For this current Phase 0, create only the two documentation files, report the results, and wait for my review and explicit approval before any implementation work begins.

## Final response

After creating the two documents, provide:

- A concise summary of the architecture and key technical decisions.
- A summary of the implementation phases.
- Any unresolved decisions requiring my approval.
- Confirmation that only the two authorized documentation files were created.
- A direct request for my approval before starting Phase 1.

Then STOP. Do not begin Phase 1 or implement anything else.
