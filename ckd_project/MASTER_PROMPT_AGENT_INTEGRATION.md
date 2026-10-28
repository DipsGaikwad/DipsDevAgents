# Master Prompt: Integrate CKD Clinical Assessment Agents Without Changing the UI

You are a senior full-stack AI engineer working on the supplied CKD Care project. Modify the actual supplied source code, not a mock implementation. Preserve the existing React UI design, component styling, routes, and user experience; make only the minimum UI changes required for the requested functionality.

## Required changes

1. Add a Doctor/Admin-only **Assess patient** action on the existing patient profile. It must call `POST /patients/{patient_id}/analyze`, execute the complete agent pipeline, persist the analysis, refresh the patient data, and surface success/failure to the user. Do not create a disconnected button that does not invoke the backend.
2. Generate both `patient_id` and `source_patient_id` on the backend for newly created patients when omitted. Do not require the user to enter either ID in the Add Patient form. Return the generated patient ID and use it to open/refresh the saved patient. Preserve all existing patient IDs, source identifiers, primary keys, foreign keys, and historical records. Do not perform a destructive schema migration. `source_patient_id` must be unique within `source_code`; use collision-safe generation in production and handle concurrent requests safely.
3. Integrate all analysis components into one working orchestration pipeline:
   - Data Validation Agent, with eGFR calculation embedded as a helper/component within this agent (not as a standalone graph node).
   - Trend Analysis Agent.
   - CKD Progression Prediction Agent.
   - SHAP Explanation Agent.
   - Patient Prioritization Agent.
   The orchestrator must call them in order, pass results between them, route invalid data safely, and return a coherent result.
4. Ensure the API endpoint used by the UI calls the orchestrator and persists the result. Do not claim an agent is integrated merely because a file exists.
5. If model loading or prediction fails, return `UNASSESSED` or a clearly labeled rule-based screening fallback. Never fabricate a model probability. Clearly distinguish clinical review priority from a clinical diagnosis or treatment recommendation.
6. Preserve the RAG clinical evidence path as a separate, complementary feature; RAG should provide source-grounded clinical information, not replace numerical progression prediction.
7. Add/update tests for ID generation, missing-eGFR calculation, graph execution, assessment API integration, invalid data, and graceful model/SHAP failure.
8. Keep credentials out of source control. Document `.env` setup, migrations, install commands, and run commands.

## Acceptance criteria

- Existing UI layout and CSS remain intact.
- A doctor can open a patient and explicitly run an assessment.
- Both IDs are generated when creating a new patient with blank/omitted IDs.
- The saved assessment includes validation status, eGFR calculation notes, longitudinal trend, prediction status/probability when valid, explanation output, prioritization and limitations.
- Every agent/component is invoked by the actual orchestrator used by the API.
- Python compilation and automated tests pass; frontend production build passes when dependencies are available.
- Report exactly what was changed, which tests ran, what could not be tested, and any clinical/model limitations. Do not claim success for untested behavior.
