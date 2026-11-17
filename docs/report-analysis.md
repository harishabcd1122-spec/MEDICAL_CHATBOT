# Phase 2: Medical Report Analysis

## Scope

Phase 2 adds authenticated upload and deterministic, educational extraction for medical reports. It does not change the Phase 1 symptom model, symptom normalization, emergency/urgency engines, or authentication implementation. It does not diagnose, recommend treatment, or change medication.

## Supported Files and Extraction

- PDF (`application/pdf` signature plus `%PDF-` header)
- PNG (PNG signature plus Pillow decoder validation)
- JPG/JPEG (JPEG signature plus Pillow decoder validation)
- Default maximum upload size: 10 MiB. Configure with `HEALTH_REPORT_MAX_UPLOAD_BYTES`.
- PDF text is extracted locally with the already-declared `pypdf` dependency. Empty, malformed, encrypted, oversized-page-count, and textless scanned PDFs return safe errors.
- Images are validated with Pillow. OCR is attempted only when both the local `tesseract` executable and `pytesseract` Python module exist. This installation has no local Tesseract OCR executable; image uploads therefore return an explicit OCR-unavailable message. Scanned PDF conversion/OCR is not configured here either.
- Uploaded bytes are saved briefly under a generated name in the operating system temporary directory, outside the static frontend. The temporary directory is removed after processing. Raw extracted report text and the original document are not persisted.

## Extraction Rules

- Known medical terms come only from the existing `medical_terms` table; only the stored simple explanation/category/source are returned.
- Known test names and configured labels for analytes already described by the existing lab-test knowledge base are matched in extracted text.
- A numeric result is considered only when it immediately follows a recognized label on the same line. Dates, identifiers, phone numbers, addresses and page numbers without a recognized result label are not treated as lab values.
- A reference interval/bound is extracted only when text explicitly labels it as a reference, ref, normal, or range. Only that extracted range can produce `WITHIN PROVIDED RANGE`, `BELOW PROVIDED RANGE`, or `ABOVE PROVIDED RANGE`.
- If a value is read but no range is explicitly present, the result is `REFERENCE RANGE NOT PROVIDED` and the response says: “Reference range was not provided in the uploaded report.” If a recognized test is named but no adjacent number is clear, it is `VALUE NOT CLEARLY DETECTED`.
- Unknown test labels are not included as medical results. No values, ranges, diagnoses, causes, or treatments are generated from inference.

## Storage and Ownership

The implementation reuses the existing `reports` and `report_values` tables; no database schema migration was needed.

- `reports.user_id` is taken from the existing authenticated user dependency.
- Each report query, analysis retrieval, and delete is scoped by both report ID and current user ID. Non-owned reports return 404 to avoid revealing their existence.
- The existing `summary_text` column stores only the structured JSON extraction. `report_values` stores the extracted label/value/unit, explicit reference range (or null), and status.
- The existing `secure_filename` column receives a random opaque identifier, not a reusable filesystem path. The actual temporary file is removed before the request finishes.
- API responses never include the stored identifier or filesystem paths. Summaries may contain personal health information, so they are only returned to the authenticated owner and can be deleted.

## API

All endpoints below require `Authorization: Bearer <existing Phase 1 token>`.

- `POST /reports/upload`: multipart form field `upload`; validates, processes, and persists a structured summary. Returns 201 with report metadata and extracted analysis.
- `GET /reports`: returns only the current user's saved report summaries.
- `GET /reports/{report_id}`: returns the current user's report and values.
- `POST /reports/{report_id}/analyze`: returns the already processed structured summary. The original file/raw text is intentionally not retained for a second extraction pass.
- `DELETE /reports/{report_id}`: deletes the report and its child values; returns 204. Foreign-key cascade is enabled by the shared SQLite connection.

Upload errors use 413 for size/page limits, 415 for unsupported or signature-mismatched file types, 422 for unreadable/corrupt/empty/OCR-unavailable documents, and generic sanitized 500 messages for internal failures. Ownership failures return 404; absent/invalid authentication uses the existing 401 behavior.

## Frontend

`frontend/report-analysis.html` is protected using the existing session guard. The dashboard links to it. `frontend/js/report-analysis.js` supports file picker and drag/drop, client-side extension/size feedback, upload and processing status, structured results, saved history, and delete. Result fields are rendered with text nodes/textContent; report text is never inserted as HTML. The shared API helper omits a manual content type for `FormData` so the browser supplies the multipart boundary.

## Tests and Limitations

Backend tests use an explicitly labeled synthetic/demo PDF generated in memory. They cover authentication, text extraction, range handling, identifiers not treated as values, unsupported/mismatched/oversized/corrupt/empty/scanned documents, OCR-unavailable behavior, unknown test handling, ownership/list/delete isolation, cascade deletion, and malformed stored summaries.

Current limitations:

- OCR is unavailable in this installation. Image/scanned content is not extracted; no OCR success is simulated.
- Extraction uses conservative recognized labels and line-local value/range association. Complex multi-column, table-wrapped, handwritten, or split-line reports may not parse reliably and should be reviewed against the original document by a healthcare professional.
- Reference range comparison is a textual numeric comparison; units are displayed but not converted or clinically reconciled.
- Persisted structured summaries contain sensitive health information. This prototype relies on the existing account/JWT controls and local SQLite storage; it does not encrypt those database fields at rest.
- No real patient report is used as a test fixture or evidence of medical accuracy.
