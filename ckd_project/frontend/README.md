# CKD Care frontend (replacement bundle)

This replacement uses the existing React/Vite + Recharts + Lucide stack and keeps the same CKD Care workspace sections (Dashboard, Patients, Visits, Risk Stratification, Reports, Knowledge Base and Profile/Settings). Demo patient records have been removed: the workspace requires a successful FastAPI login and loads records from MySQL.

## Run
1. Copy this folder over your existing `frontend` folder after backing up the old folder.
2. Open a terminal in this folder and run `npm install`.
3. Copy `.env.example` to `.env` (frontend env, not your root backend `.env`) and keep `VITE_API_BASE_URL=http://localhost:8000`.
4. Start it using `npm run dev`.

Use your existing root `.env` for the backend database connection. Login supports username or email. Sign-up is for DOCTOR/DEO only and accounts must be approved by an Admin.

## Notes
- White/dark theme remains supported. UI is styled to match the current blue/white clinical CKD Care layout and existing section names; this is a replacement build, not a byte-for-byte copy of your original `App.jsx`/`styles.css`.
- RAG is intentionally not connected. Knowledge Base upload stores the document and metadata; it does not index the document or generate embeddings.
- AI risk labels are not derived from rules in this UI. Only backend saved analysis results are shown. The trained model artifact is not included because the original project ignores model artifacts in Git; the `/predict` endpoint requires the local `models/trained/ckd_model.joblib` file.
- This is an academic prototype and has not been validated for real patient care or production deployment.
