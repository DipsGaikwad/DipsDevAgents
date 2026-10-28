# MASTER PROMPT: Fix RAG Knowledge Base, Integrate a Free LLM, and Repair Profile Dropdown in CKD Care Agent

## 1. Project Context

I am developing an MCA project titled:

**Agentic AI-Driven CKD Progression Prediction and Clinical Decision Support using RAG**

The application is an existing, integrated project with a React frontend, FastAPI backend, MySQL database, AI-based CKD progression prediction, multiple agents, and a clinical decision-support interface.

The project is already running, and its existing features are working correctly. I do NOT want the application to be rebuilt from scratch.

Your task is to investigate and fix only the three issues described below while preserving all existing working functionality.

## 2. Strict Development Rules

Before modifying anything:

1. Inspect the actual project directory, folder structure, dependencies, configuration files, backend routes, frontend components, authentication implementation, database models, and existing AI-agent architecture.
2. Trace each issue from the frontend action to the backend endpoint and, where applicable, to the database, document processor, vector database, or LLM.
3. Identify the root cause before implementing a fix. Do not assume that the problem is caused by a missing package or a single incorrect API endpoint.
4. Reuse the existing architecture and dependencies wherever practical. Avoid unnecessary packages, duplicate services, duplicate agents, or parallel implementations.
5. Preserve the existing UI layout, theme, navigation, dashboard, patient management, visit management, prediction workflow, reports, notifications, authentication, and other working features.
6. Make only targeted changes required to resolve the issues.
7. Never replace working functionality with mock responses, hardcoded results, simulated RAG responses, or placeholder LLM outputs.
8. Never expose API keys, passwords, JWT secrets, or other credentials in frontend code, logs, source control, or generated documentation.
9. Do not delete existing patient data, database tables, vector collections, or knowledge-base documents as a workaround.
10. Do not claim a fix is complete until it has been tested. Report any tests that could not be performed because of missing credentials, unavailable services, or environment limitations.

## 3. Issue One: Knowledge Base and RAG Are Not Working

### Current Problem

The application contains a Knowledge Base/Resources interface where users can add documents. Document addition is failing with errors, and the clinical assistant's document-indexing functionality is also not working reliably.

The backend logs contain requests such as:

- `GET /resources` — successful in some requests, but also returns `401 Unauthorized`.
- `POST /resources` — returns `401 Unauthorized`.
- `GET /clinical-assistant/status` — returns `401 Unauthorized`.
- `POST /clinical-assistant/index/3` — returns `401 Unauthorized`.

The logs also contain an initial MySQL connection error:

`pymysql.err.OperationalError: (2003, "Can't connect to MySQL server on '127.0.0.1'")`

Subsequent login and application requests succeed. Investigate these errors independently rather than assuming they all share one cause.

### Required Investigation

Trace the complete document-ingestion workflow:

Frontend document upload or add-resource action → HTTP request → authentication middleware/dependency → FastAPI route → document extraction → text cleaning → chunking → embedding generation → vector database insertion → indexing status → retrieval.

Inspect:

- The frontend Knowledge Base/Resources components and their upload handlers.
- API endpoint URLs, HTTP methods, request payloads, multipart form handling, and response parsing.
- JWT creation, token storage, token refresh or expiration handling, and authorization headers.
- FastAPI authentication dependencies and role/permission checks.
- Resource/document database models and their relationships.
- Supported file types, file-size validation, temporary-file handling, and text extraction.
- PDF, TXT, DOCX, and other formats already intended to be supported by the project.
- Chunking configuration and embedding model initialization.
- ChromaDB or whichever vector database the existing project actually uses.
- Collection creation, persistence directories, metadata, document IDs, and duplicate-document handling.
- Error handling and status updates when extraction, embedding, or indexing fails.

Do not assume that all listed file types are already supported. Confirm the existing implementation and dependencies.

### Required RAG Implementation

Implement or repair a genuine Retrieval-Augmented Generation pipeline using the existing architecture.

**Ingestion pipeline:**

1. Accept and validate a supported document.
2. Extract its text.
3. Clean and normalize the extracted text without changing its clinical meaning.
4. Split the text into appropriately sized overlapping chunks.
5. Generate embeddings using a configured embedding model.
6. Store the vectors, text chunks, document metadata, and identifiers persistently in the existing vector database.
7. Save and maintain resource metadata and indexing status in MySQL if that is the existing persistence design.
8. Return an accurate success or failure response to the frontend.
9. Ensure failed ingestion is visible and diagnosable rather than silently reported as successful.

**Retrieval and answering pipeline:**

1. Accept a doctor's clinical question.
2. Generate the query embedding using the same compatible embedding model used during ingestion.
3. Retrieve the most relevant indexed chunks.
4. Apply appropriate similarity filtering and context limits.
5. Pass the retrieved evidence and question to the configured LLM.
6. Generate an answer grounded in the retrieved evidence.
7. Return the answer together with available source-document names, relevant citations or chunk references, and retrieval metadata where appropriate.
8. If no relevant evidence is retrieved, explicitly state that the Knowledge Base does not contain sufficient supporting information. Do not fabricate citations or pretend that retrieval succeeded.
9. Keep document indexing and clinical question answering as distinct operations.

### Required Tests

Verify that:

- An authenticated, authorized user can add a valid document.
- Invalid or unsupported documents produce clear errors.
- A document is actually extracted, chunked, embedded, and persisted.
- Indexing status accurately reflects success or failure.
- The indexed document remains available after backend restart.
- A question about content in the document retrieves relevant chunks.
- The assistant returns a grounded answer with valid source references.
- A question unrelated to the indexed documents does not produce fabricated source citations.
- Authentication failures are handled correctly.
- Existing Resources and Knowledge Base functionality continues to work.

Do not rebuild or delete the existing vector database merely to make the tests pass.

## 4. Issue Two: Integrate a Free-of-Cost LLM for Clinical Explanations

### Objective

Integrate a suitable free-to-run LLM that can explain prediction results, answer doctors' clinical questions, summarize retrieved medical evidence, and assist with clinical decision support.

Prefer a locally hosted model using **Ollama**, provided it is compatible with the project's operating environment and hardware. This avoids per-token API charges and does not require a paid hosted inference API.

However, inspect the current implementation first. Reuse an existing provider abstraction if available, and avoid replacing a functioning component unnecessarily.

### Model and Configuration Requirements

1. Select a suitable instruction-following model that is available for local use and fits the machine's RAM, VRAM, and performance constraints.
2. Select a compatible embedding model for RAG separately. Do not assume that the LLM and embedding model are interchangeable.
3. Store model names, provider settings, and service URLs in backend environment configuration.
4. Never place model credentials or private configuration in React source code.
5. Add a clear backend health/status check for LLM availability.
6. Handle Ollama being unavailable, the model not being downloaded, generation timeouts, and insufficient memory.
7. If a hosted free-tier provider is considered instead, document its limits, availability requirements, data-handling implications, and the possibility of usage restrictions. Do not describe a limited free tier as permanently free or unlimited.

### Clinical Assistant Behaviour

The LLM should be able to:

- Explain a patient's existing CKD progression prediction in understandable clinical language.
- Summarize the relevant patient trend, including available creatinine and eGFR observations.
- Explain existing model-generated SHAP feature contributions when those outputs are available.
- Retrieve and summarize relevant evidence from the Knowledge Base.
- Answer a doctor's question using retrieved documents and clearly identified patient-analysis results.
- Distinguish measured patient data, model predictions, retrieved evidence, and LLM-generated interpretation.
- State when the available information is insufficient.
- Avoid inventing laboratory values, patient history, model probabilities, clinical guidelines, or source references.

The LLM must NOT replace the trained numerical prediction model, calculate invented risk probabilities, or independently assign a progression label unsupported by the prediction system.

Use a clear response structure when appropriate:

1. Clinical question or task.
2. Relevant patient findings.
3. Prediction and its limitations.
4. Evidence retrieved from the Knowledge Base.
5. Explanation and clinical considerations.
6. Missing information or uncertainty.
7. Source references.

This is a clinical decision-support tool, not an autonomous diagnostic or treatment system. The final clinical decision remains with the qualified doctor. Do not present generated content as validated medical advice.

## 5. Investigate the Existing Explanation Agent

An explanation agent is part of the intended multi-agent architecture. Determine whether it already exists, where it is implemented, and whether it is connected to the actual prediction workflow.

Search the project for:

- Explanation Agent modules and classes.
- SHAP-related calculations and outputs.
- LangGraph graph nodes and edges.
- The graph orchestrator and state schema.
- Patient analysis and prediction API routes.
- Clinical assistant or chat endpoints.
- RAG retrieval functions and LLM generation functions.
- Frontend components displaying explanations.
- Existing prompts, response schemas, and stored analysis results.

Produce an explicit execution trace:

**Doctor action → frontend handler → API endpoint → orchestrator or agent → model/SHAP outputs → RAG retrieval, if relevant → LLM generation → API response → frontend display.**

Clearly distinguish these responsibilities:

- **Prediction Agent:** produces the numerical model prediction and associated risk or progression output.
- **Trend Analysis Agent:** analyzes longitudinal patient measurements.
- **SHAP Explanation Agent:** explains model feature contributions using actual SHAP outputs.
- **RAG Retrieval:** retrieves relevant information from indexed medical documents.
- **LLM Explanation/Clinical Assistant:** converts verified analysis results and retrieved evidence into a readable explanation for the doctor.
- **Orchestrator:** coordinates the existing workflow where appropriate.

These are logical responsibilities; do not create duplicate agents if equivalent components already exist.

If the current Explanation Agent is disconnected, connect it to the actual workflow. If it exists but only generates static text, replace that behaviour with genuine explanations based on the available outputs. If the LLM is used for natural-language explanations, keep SHAP calculations and numerical predictions grounded in their existing model implementations.

Determine whether explanation generation should occur automatically after a successful patient assessment, on demand through a doctor action, or both, based on the existing UI and architecture. Preserve current user interactions unless a change is necessary.

### Explanation Tests

Verify that:

- The explanation corresponds to the correct patient and analysis.
- SHAP values are actual model-derived values, not LLM-invented feature importance.
- Patient data and retrieved documents are passed to the LLM only when authorized and necessary.
- The explanation does not invent missing data or unsupported claims.
- LLM failure does not corrupt or prevent the core numerical prediction from being stored.
- Existing prediction and report generation remain functional.

## 6. Issue Three: Profile Dropdown Is Not Working

### Current Problem

The profile dropdown is visible or expected in the existing UI, but its interactions are not functioning correctly.

### Required Investigation

Inspect the React component responsible for the profile avatar, dropdown menu, and click handling.

Check:

- Whether the click handler is attached to the correct element.
- Whether dropdown visibility state is updated correctly.
- Whether event propagation, outside-click handling, or click-away logic closes it immediately.
- Whether the menu is hidden behind other components due to `z-index`, overflow, positioning, or stacking contexts.
- Whether conditional rendering or CSS prevents the menu from appearing.
- Whether the profile data request is successful and the returned response matches the expected structure.
- Whether menu items point to valid routes or trigger working actions.
- Whether the dropdown is affected by stale authentication state or failed API requests.

### Required Behaviour

Without redesigning the interface:

1. Clicking the profile avatar opens the dropdown.
2. Clicking the avatar again toggles it closed.
3. Clicking outside closes it.
4. Pressing Escape closes it.
5. The dropdown displays the correct authenticated user's available profile information.
6. Existing menu actions—such as Profile, Settings, or Logout—work according to the project's current functionality.
7. Logout clears the appropriate authentication state and redirects the user to the existing login flow.
8. The dropdown behaves correctly after page refresh and login.
9. The menu remains usable at the existing responsive breakpoints.

Do not add menu items that do not exist in the project requirements. Do not change the overall navbar, theme, dashboard, or page layout.

## 7. Authentication and MySQL Checks

Because the provided backend logs show intermittent `401 Unauthorized` responses and an initial MySQL connection-refused error, verify the following across all three issues:

- Whether the frontend attaches a valid access token to protected API requests.
- Whether tokens are missing, expired, overwritten, or read from the wrong storage location.
- Whether the backend uses consistent authentication dependencies.
- Whether admin/doctor permissions are enforced intentionally and correctly.
- Whether the API client consistently attaches authentication headers.
- Whether the MySQL service is running and the configured host, port, database, and credentials are correct.
- Whether connection failures are handled clearly without causing unrelated frontend failures.

Do not remove authentication requirements or make protected endpoints public merely to eliminate `401` errors. Fix token handling and authorization logic according to the existing security model.

Treat database connectivity as a separate infrastructure check. Do not change database configuration or schema without evidence that it is required.

## 8. Development Order

Resolve the issues in this exact sequence, and finish testing each stage before moving to the next:

**Phase 1 — Diagnosis**
- Inspect the repository and identify the exact files, routes, components, services, and dependencies involved.
- Reproduce the issues.
- Identify the root cause of each issue.
- Present a short diagnosis and proposed minimal changes.

**Phase 2 — Repair Knowledge Base and RAG**
- Fix authentication and document-ingestion failures.
- Complete persistent indexing and retrieval.
- Test the complete ingestion-to-answer workflow.

**Phase 3 — Integrate the Free LLM and Connect Explanations**
- Configure the chosen LLM and embedding model.
- Connect genuine RAG retrieval to LLM generation.
- Trace and connect the existing Explanation Agent.
- Test patient-specific explanations and evidence-grounded answers.

**Phase 4 — Repair Profile Dropdown**
- Fix dropdown interactions and existing menu actions.
- Verify profile data and logout behaviour.

**Phase 5 — Regression Testing**
- Test login, authentication, patient creation/editing, visit recording, patient assessment, progression prediction, trend analysis, SHAP explanation, reports, notifications, Resources, Knowledge Base, clinical assistant, and profile dropdown.
- Confirm the existing UI is preserved.
- Check backend logs and frontend console for new errors.

## 9. Required Deliverables

After completing the work, provide:

1. Root cause of each issue, supported by observed code or test evidence.
2. A list of every file modified and why.
3. Any dependencies added or changed, with justification.
4. Exact environment variables required, using placeholder values rather than real secrets.
5. Setup commands for the selected local LLM and embedding model.
6. Any database migration or schema changes, with safe instructions.
7. API endpoints and request formats involved in the repaired workflow.
8. Actual test results, including failed or unexecuted tests.
9. Instructions for starting the backend and frontend.
10. A concise manual testing checklist for the developer.
11. Any remaining limitations, including model latency, local hardware constraints, or medical-validation requirements.

If creating downloadable modified files or a ZIP, use the actual project files, preserve the folder structure, and verify that the generated artifacts exist. Do not claim that the application is fully working unless the relevant integration tests have actually passed.

## Final Constraint

**Fix the existing application, do not rebuild it. Preserve every currently working feature and the existing UI. Prioritize a genuine, persistent RAG pipeline, a free-to-run LLM for grounded clinical explanations, and a functioning profile dropdown. Diagnose before modifying, implement incrementally, and verify every change.**