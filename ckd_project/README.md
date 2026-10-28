# CKD Care — Clinical Decision Support System

The original React UI and CSS are preserved. This package includes the backend agent integration and a prototype progression model.

**Start here:** [Agent integration, setup, migration, and model limitations](README_AGENT_INTEGRATION.md).

Quick start:
1. Use Python 3.11/3.12 and install `pip install -r backend\requirements.txt`.
2. Copy `.env.example` to `.env` and configure MySQL/JWT settings.
3. Apply your existing database schema migrations, then run `CKD_Agent_Integration_Migration.sql`.
4. Start backend with `python -m uvicorn backend.app:app --reload --port 8000`.
5. Start frontend with `cd frontend`, `npm install`, `npm run dev`.

This is an academic prototype, not a validated medical device. Model output and calculated eGFR require clinician verification and must not drive autonomous treatment decisions.
