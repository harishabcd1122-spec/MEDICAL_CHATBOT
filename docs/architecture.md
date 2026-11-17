# HealthBridge AI — System Architecture & Workflow

## 1. Architectural Philosophy: The Controlled Hybrid Safety Architecture

HealthBridge AI is deliberately designed to **prevent unconstrained LLM hallucinations in medical contexts**. Rather than routing user medical inquiries directly to a generative language model, the system operates on a multi-stage gated pipeline:

```
                      [ User Input / Voice / Document ]
                                      │
                                      ▼
                        [ Input Normalization & Security ]
                                      │
                                      ▼
                      [ Emergency Safety Engine (Rule-based) ]
                                ╱           ╲
                 [Emergency Detected]    [No Acute Emergency]
                         │                         │
                         ▼                         ▼
             [Immediate Life-Saving]     [Intent Classification]
              Emergency Triage Card]               │
                                         ┌─────────┴─────────┐
                                         ▼                   ▼
                               [Symptom Assessment]  [Knowledge Lookup]
                                         │                   │
                                         ▼                   ▼
                                [Feature Encoding]   [Curated DB Query]
                                         │                   │
                                         ▼                   ▼
                                [Trained Prototype]  [Static Knowledge Data]
                                 Selected Classifier         │
                                         │                   │
                                         ▼                   ▼
                                [Model Match Score]   [Language Selector]
                                         │             (EN / TA / HI)
                                         ▼                   │
                                [Urgency Safety Engine]      │
                                (Low / Moderate / Urgent)    │
                                         │                   │
                                         └─────────┬─────────┘
                                                   │
                                                   ▼
                                      [Plain-Language Formatter]
                                                   │
                                                   ▼
                                      [Global Medical Disclaimer &
                                       Doctor Questions Generator]
                                                   │
                                                   ▼
                                            [User Response]
```

## 2. Core Subsystems

### A. Emergency Safety Engine (Rule-Based Gate)
- **Execution Order**: Pre-inference. Always executes before machine learning scoring or knowledge queries.
- **Trigger Indicators**: Crushing chest pain, severe dyspnea, anaphylaxis signs, stroke indicators (FAST), uncontrollable hemorrhaging, syncope/loss of consciousness.
- **Response**: Immediate overriding emergency guidance, telephone triage recommendation, avoiding long explanatory text.

### B. Machine Learning Engine & Model Match Score
- **Models Evaluated**: Random Forest (Baseline), Logistic Regression, and Decision Tree; selected using validation macro F1.
- **Dataset**: Synthetic/demo rows generated from hand-authored symptom profiles. This is not a sourced clinical dataset.
- **Evaluation Criteria**: Multi-class Precision, Recall, F1-Score, and confusion matrix on an untouched stratified test split after model selection. Results characterize only the synthetic generator.
- **Score Nomenclature**: Strictly **"Model Match Score"**. The system forbids labeling this score as "diagnostic certainty", "disease probability", or "clinical confidence".
- **Uncertainty Guardrails**: Returns out-of-scope notifications when the recognized symptoms do not match the supported prototype scope. This is not a clinical diagnostic threshold.

### C. Urgency & Triage Safety Engine
- Assigns **Urgency/Safety Level**:
  - `LOW`: Mild, self-limiting symptom patterns without red-flag indicators.
  - `MODERATE`: Persistent, acute, or progressive presentations warranting medical consultation.
  - `URGENT`: Elevated symptom combinations indicating potential complications requiring prompt clinical care.

### D. Curated Knowledge & Terminology Subsystem
- Serves static JSON records for disease profiles, medical terms, and laboratory tests through SQLite. Source attribution is present but not uniformly backed by record-level URLs; entries have not been independently verified as part of this audit.
- Multilingual explanations: English, Tamil (தமிழ்), and Hindi (हिन्दी).
- No generative answer model is used on these lookup routes. Unknown terms and laboratory tests return a fixed safe-information response; unknown diseases return an out-of-scope response.

### E. Data Access & Privacy Architecture
- SQLite with parameterized SQL. Phase 1 exposed the authenticated current-user profile; Phase 2 adds owner-scoped report routes backed by the existing report tables. Other appointment/reminder resource APIs remain outside the current scope.
- Password security uses salted bcrypt hashing and JWT authorization. Configure `JWT_SECRET` in production; local development generates an ephemeral signing key.

## 3. Phase 2: Medical Report Analysis

- Authenticated report routes reuse the Phase 1 JWT/current-user dependency and existing SQLite `reports` and `report_values` tables. Every list/read/analyze/delete query is filtered by `user_id`; a report owned by another user is returned as not found.
- PDF/PNG/JPG/JPEG uploads are size-limited, extension-checked and signature/decoder-checked. The default limit is 10 MiB and is configurable with `HEALTH_REPORT_MAX_UPLOAD_BYTES`.
- Files are written under an unpredictable name to a system temporary directory outside the static frontend, parsed, then removed. Uploaded bytes and extracted raw text are not retained. SQLite stores a sanitized display filename, opaque processing identifier, MIME type, structured JSON summary, and parsed values/ranges/statuses.
- Text PDFs are parsed locally with `pypdf`. Images and scanned PDFs require local OCR; no paid/external OCR or LLM is required. If the local OCR dependencies are unavailable, the API explicitly rejects unreadable scanned content without claiming extraction succeeded.
- Medical terms are looked up only in the existing terminology table. Lab tests are matched against the existing laboratory test list and a small set of labels for analytes already described by those tests. Values are only accepted next to a recognized label. A result is compared only with an explicitly detected reference range from the same report line.
- The report summary is educational and non-diagnostic. It does not infer causes, recommend treatment, or substitute ranges from general knowledge. Unknown test labels are omitted rather than interpreted.
- API details, processing limits, endpoints and coverage are documented in `docs/report-analysis.md`.
