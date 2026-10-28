# CKD Care API

Run commands from the project root so `backend` imports resolve. Python 3.11 or 3.12 is recommended.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with the local MySQL URL and a long random `JWT_SECRET_KEY`. Create the `ckd_project` database, apply your existing schema migrations, then apply `CKD_Agent_Integration_Migration.sql` to create the saved-analysis table. Do not commit `.env`.

Create the initial administrator using `python -m backend.bootstrap_admin`, then start the backend:

```powershell
python -m uvicorn backend.app:app --reload --port 8000
```

Health check: `http://localhost:8000/health`; API docs: `http://localhost:8000/docs`.

## Agent workflow

`eGFR calculator → data validator → trend analyzer → progression predictor → SHAP explainer → prioritization`. Adding a visit runs and saves an analysis after the visit is committed. Re-run with authenticated `POST /patients/{patient_id}/analyze` as an Admin or Doctor. Analysis results are exposed as `latest_analysis` in patient records.

The included model is a prototype trained on the included processed dataset. Its holdout ROC-AUC was approximately 0.61; it is not externally validated or intended for clinical use. eGFR estimates and all outputs require clinician verification. See `README_AGENT_INTEGRATION.md` for full setup and limitations.
