# Phase 1 Verification Report

**Date:** 2026-09-27  
**Scope:** Phase 1 verification only. Phase 2 was not started.

## Test Result

Command: `pytest -v backend/tests`

**Result: 14 passed, 0 failed.** The final full run completed in 6.95s.

```text
backend/tests/test_auth.py::test_register_and_login_flow PASSED
backend/tests/test_auth.py::test_password_mismatch PASSED
backend/tests/test_auth.py::test_invalid_login PASSED
backend/tests/test_auth.py::test_unauthorized_access PASSED
backend/tests/test_knowledge_and_search.py::test_list_and_get_diseases PASSED
backend/tests/test_knowledge_and_search.py::test_disease_not_found PASSED
backend/tests/test_knowledge_and_search.py::test_list_and_get_medical_terms PASSED
backend/tests/test_knowledge_and_search.py::test_global_search PASSED
backend/tests/test_knowledge_and_search.py::test_ml_evaluation_endpoint PASSED
backend/tests/test_symptoms_and_safety.py::test_emergency_engine_detection PASSED
backend/tests/test_symptoms_and_safety.py::test_symptom_normalizer PASSED
backend/tests/test_symptoms_and_safety.py::test_symptom_api_emergency_override PASSED
backend/tests/test_symptoms_and_safety.py::test_symptom_api_valid_matching PASSED
backend/tests/test_symptoms_and_safety.py::test_symptom_api_insufficient_information PASSED
============================== 14 passed in 6.95s ==============================
```

No pytest failures required repair. The ML evaluation and JWT configuration were corrected during this audit, and the complete suite was rerun afterward.

## Backend and API

Uvicorn started with `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`; application startup completed and `/api/health` returned `healthy`. It was stopped after the live checks.

The live OpenAPI document exposes 13 paths, all exercised through a combination of live requests and the test suite:

- `GET /api/health`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /symptoms/analyze`
- `GET /diseases`, `GET /diseases/{disease_id}`
- `GET /medical-terms`, `GET /medical-terms/{term_id}`
- `GET /lab-tests`, `GET /lab-tests/{test_id}`
- `GET /search`
- `GET /ml/evaluation`

Supported records returned successfully; unsupported disease lookup returned 404/out-of-scope, and unknown medical-term/lab-test lookups returned 404 with the safe-information message. Search and evaluation returned successfully.

## Database and Authentication

- SQLite initialization and connectivity succeeded at the configured local database path.
- Schema initialization created 11 application tables (plus SQLite's internal sequence table); the seeded knowledge counts are 20 diseases, 42 medical terms, and 11 lab tests.
- `PRAGMA foreign_key_check` returned zero violations.
- Registration returned 201; login returned a bearer token; authenticated `/auth/me` returned the matching user. Invalid credentials and a missing token returned 401.
- The stored test-account password was verified as a bcrypt hash and successfully checked against the test password. The API response did not expose `password_hash`.
- There are no report, appointment, reminder, or timeline API routes in this Phase 1 surface. Cross-user access to those resource types is therefore not testable; `/auth/me` is the only protected resource route found.
- A known hardcoded JWT fallback key was removed. Local development now generates an ephemeral process key; production import fails when `APP_ENV=production` and `JWT_SECRET` is missing. Configure `JWT_SECRET` in the production process environment. The application does not load `.env` files itself.

## ML Pipeline

- **Dataset source:** `ml/data/disease_symptoms_dataset.csv` is synthetic/demo data, not a sourced patient or clinical dataset. It contains 1,200 generated rows, 42 binary symptom features, and 20 balanced disease labels. Regenerating it with `generate_dataset(samples_per_disease=60, random_seed=42)` exactly reproduced the CSV.
- **Provenance correction:** The prior documentation's claims of derivation from named external benchmarks and PDDL/CC-BY licensing were unsupported by the repository and have been withdrawn. Profiles in `prepare_dataset.py` are hand-authored assumptions, not clinically validated probabilities.
- **Preprocessing and splits:** There is no data-fitted normalization or imputation before splitting. Train/validation/test partitions use stratified grouping by complete feature vector. Final sizes were 719/241/240 rows; exact duplicate feature vectors had zero overlap between each pair of partitions. Model selection uses validation macro F1; the selected model is refit on the 960 train+validation rows and evaluated once on the untouched test partition.
- **Model used:** Random Forest (Baseline), selected from validation results. The saved artifact is `ml/models/best_model.joblib`.
- **Held-out synthetic test metrics:** accuracy 0.9917; macro precision 0.9920; macro recall 0.9917; macro F1 0.9915. The generated 20x20 confusion matrix and per-model validation comparisons are in `ml/evaluation/metrics.json`.
- These figures are measurements from the synthetic generator only. They are not clinical diagnostic accuracy and provide no evidence of real-patient performance. The evaluation artifact and API now explicitly identify the dataset as `synthetic_demo`.
- Saved-model inference and the evaluation endpoint were verified after retraining.

## Safety and Symptom Checks

- The exact input `I have fever, headache and body pain.` normalized to `fever`, `headache`, and `body_pain`, returned possible conditions, and included a Model Match Score, urgency level, explanation, and disclaimer. The current urgency rule returned `LOW` for this input.
- The displayed score was 47.6% and included the explicit caveat: it is **not** the probability that the user has a disease and is not a medical diagnosis. It was not described as diagnosis probability or clinical confidence.
- `I feel strange.` returned `insufficient_information` with “I don't have enough reliable information...” guidance.
- `I have severe chest pain and difficulty breathing.` returned `emergency_detected`, urgent-care guidance, and zero possible conditions. Emergency screening runs before normalization/inference in the route; the response did not name or diagnose an emergency condition.
- Emergency and urgency engines are deterministic keyword/rule systems. Their coverage is limited and is not a substitute for clinical triage.

## Knowledge Base and Medical Claims

- The static JSON/SQLite lookup contains 20 diseases, 42 medical terms, and 11 laboratory tests. All entries have a source attribution; all disease entries also have a source URL. Terms and lab tests do not have per-record source URLs.
- No generative LLM call path was found in the backend lookup implementation. Lookups return stored records; unknown terms and tests return fixed safe text, and unknown diseases return an out-of-scope response.
- This verifies that the application is not inventing lookup entries at request time. It does **not** establish that every medical statement is accurate: source attributions were not independently checked against authoritative publications, especially for terms and laboratory tests. Independent clinical/source review remains outstanding.

## Security and File Hygiene

- No `.env` file is present. `.env.example` contains placeholders, not production credentials.
- `.gitignore` covers `.env` and `.env.*` (while allowing `.env.example`), database/SQLite files and WAL/SHM companions, uploads, Python cache files, and `.joblib`/`.pkl` model files under `ml/models`.
- `uploads/` contained only `.gitkeep` during the audit.
- The similarly named API and schema files are distinct: `backend/app/api/auth.py` versus `backend/app/schemas/auth.py`, and `backend/app/api/symptoms.py` versus `backend/app/schemas/symptoms.py`. `main.py` and `security.py` each have one source copy. No identical duplicate was found among these current source files; historical overwrites cannot be determined without Git history.
- The workspace has no `.git` directory. Git status/history and tracked-file ignore behavior could not be checked, so this is a current-tree inspection only.

## Documentation and Known Limitations

The only project Markdown documentation found was `docs/architecture.md` and `docs/data_source.md`; both were corrected to reflect the implemented system and supported evidence. This report is the final Phase 1 audit artifact.

Known limitations:

- The ML dataset is synthetic; all metrics are restricted to that generator and are not clinically meaningful.
- The knowledge base has source labels but incomplete record-level links and has not undergone independent medical validation.
- Emergency/urgency coverage is rule-based and can miss unrecognized wording or clinical context.
- No user-owned resource API endpoints exist, so resource-level authorization isolation is not verified.
- Local development JWT keys are ephemeral; tokens will not survive a server restart unless `JWT_SECRET` is configured.
- No Git metadata is available to establish prior file history or baseline changes.
- Test and live-auth verification initialized/seeded the local `healthbridge.db` and created verification accounts; the database is ignored by the current ignore rules.

## Files Changed

- `.gitignore`
- `backend/app/utils/security.py`
- `ml/preprocessing/prepare_dataset.py`
- `ml/training/train_models.py`
- `ml/evaluation/metrics.json` (regenerated from the pipeline)
- `ml/models/best_model.joblib` (regenerated from the pipeline)
- `docs/architecture.md`
- `docs/data_source.md`
- `docs/PHASE1_VERIFICATION_REPORT.md` (this report)
- `healthbridge.db` (initialized/seeded and used by verification; local generated data)

## Phase 2 Recommendation

**Not ready to proceed on medical/data assurance grounds.** The Phase 1 software smoke checks pass, but the dataset is synthetic and the medical knowledge content has not been independently source-validated. Proceed only after explicitly accepting the synthetic-only model as a demo and completing review of the medical references; do not present the ML scores as clinical evidence.
