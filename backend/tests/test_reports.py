"""Phase 2 report tests use only an explicitly synthetic/demo in-memory PDF."""

from __future__ import annotations

import io
import re
from uuid import uuid4

import pytest
from PIL import Image
from pypdf import PdfReader
from fastapi.testclient import TestClient

from backend.app.api.reports import router as reports_router
from backend.app.database.connection import get_db, init_db
from backend.app.document_processing import report_analyzer
from backend.app.main import app

client = TestClient(app)
created_test_emails: set[str] = set()


@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    yield
    with get_db() as connection:
        for email in created_test_emails:
            connection.execute("DELETE FROM users WHERE email = ?", (email,))
    created_test_emails.clear()


def synthetic_demo_pdf(text: str) -> bytes:
    """Build a tiny text PDF fixture; it is not a real medical report."""
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 40 760 Td ({escaped}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)


def register_and_token(label: str) -> tuple[str, dict[str, str]]:
    email = f"phase2-{label}-{uuid4().hex}@example.com"
    created_test_emails.add(email)
    response = client.post("/auth/register", json={
        "name": f"Phase Two {label}",
        "email": email,
        "password": "SyntheticDemoPass123!",
        "confirm_password": "SyntheticDemoPass123!",
    })
    assert response.status_code == 201
    return email, {"Authorization": f"Bearer {response.json()['access_token']}"}


def upload_demo_pdf(headers: dict[str, str], filename: str = "synthetic-demo-report.pdf", text: str = "Hemoglobin: 10.2 g/dL Reference range: 12-16 g/dL"):
    return client.post(
        "/reports/upload",
        headers=headers,
        files={"upload": (filename, synthetic_demo_pdf(text), "application/pdf")},
    )


def test_unauthenticated_upload_is_rejected():
    response = client.post("/reports/upload", files={"upload": ("demo.pdf", synthetic_demo_pdf("Synthetic demo"), "application/pdf")})
    assert response.status_code == 401


def test_authenticated_pdf_upload_extracts_only_explicit_values_and_ranges():
    _, headers = register_and_token("extract")
    diagnostic_text = (
        "Synthetic/demo test report\n"
        "Hemoglobin: 10.2 g/dL Reference range: 12-16 g/dL\n"
        "Glucose: 108 mg/dL\n"
        "Patient ID: 76543210 Date: 2026-09-27"
    )
    print("ACTUAL_MULTILINE_PYPDF_TEXT:", repr(PdfReader(io.BytesIO(synthetic_demo_pdf(diagnostic_text))).pages[0].extract_text()))
    response = upload_demo_pdf(
        headers,
        text=diagnostic_text,
    )
    assert response.status_code == 201
    result = response.json()
    assert result["analysis"]["document"]["extraction_method"] == "pdf_text"
    values = {entry["test_name"]: entry for entry in result["analysis"]["detected_tests"]}
    assert "Hemoglobin" in values, result["analysis"]["detected_tests"]
    assert values["Hemoglobin"]["value"] == "10.2"
    assert values["Hemoglobin"]["unit"] == "g/dL"
    assert values["Hemoglobin"]["reference_range"] == "12-16 g/dL"
    assert values["Hemoglobin"]["status"] == "BELOW PROVIDED RANGE"
    assert values["Glucose"]["value"] == "108"
    assert values["Glucose"]["status"] == "REFERENCE RANGE NOT PROVIDED"
    assert all("76543210" not in str(item) for item in values.values())
    assert all("diagnosis" not in item.lower() for item in result["analysis"]["important_observations"])
    assert "does not provide a diagnosis" in result["analysis"]["disclaimer"]
    assert "Hemoglobin" in [term["term"] for term in result["analysis"]["medical_terms"]]
    assert "stored_filename" not in result and "secure_filename" not in result
    assert "lab_values" in result

    with get_db() as connection:
        row = connection.execute("SELECT secure_filename, summary_text FROM reports WHERE id = ?", (result["id"],)).fetchone()
    assert re.fullmatch(r"[a-f0-9]{32}\.pdf", row["secure_filename"])
    assert "Hemoglobin: 10.2" not in row["summary_text"]
    assert "Reference range: 12-16" not in row["summary_text"]


def test_path_traversal_filename_is_reduced_to_a_safe_display_name():
    _, headers = register_and_token("path")
    response = upload_demo_pdf(headers, filename="../../private-folder/synthetic-report.pdf")
    assert response.status_code == 201
    assert response.json()["filename"] == "synthetic-report.pdf"
    assert "private-folder" not in response.text
    assert "secure_filename" not in response.text


def test_upload_validation_rejects_unsupported_mismatched_oversized_and_corrupt_files(monkeypatch):
    _, headers = register_and_token("validation")
    unsupported = client.post("/reports/upload", headers=headers, files={"upload": ("report.exe", b"MZ executable", "application/octet-stream")})
    assert unsupported.status_code == 415

    mismatch = client.post("/reports/upload", headers=headers, files={"upload": ("report.pdf", b"not actually pdf", "application/pdf")})
    assert mismatch.status_code == 415

    monkeypatch.setenv("HEALTH_REPORT_MAX_UPLOAD_BYTES", "32")
    oversized = client.post("/reports/upload", headers=headers, files={"upload": ("large.pdf", b"%PDF-" + b"x" * 40, "application/pdf")})
    assert oversized.status_code == 413
    monkeypatch.undo()

    corrupt = client.post("/reports/upload", headers=headers, files={"upload": ("corrupt.pdf", b"%PDF-1.4\nnot-a-pdf", "application/pdf")})
    assert corrupt.status_code == 422
    assert "Traceback" not in corrupt.text
    assert "OneDrive" not in corrupt.text


def test_empty_and_scanned_pdfs_return_readability_errors():
    _, headers = register_and_token("readability")
    empty = client.post("/reports/upload", headers=headers, files={"upload": ("empty.pdf", b"", "application/pdf")})
    assert empty.status_code == 422
    blank_pdf = client.post("/reports/upload", headers=headers, files={"upload": ("scanned-demo.pdf", synthetic_demo_pdf(""), "application/pdf")})
    assert blank_pdf.status_code == 422
    assert "scanned" in blank_pdf.json()["detail"].lower()
    assert "ocr" in blank_pdf.json()["detail"].lower()


def test_image_ocr_unavailable_is_reported_without_claiming_success():
    if report_analyzer._ocr_available():
        pytest.skip("Local OCR is installed; image recognition requires an OCR fixture for this environment.")
    _, headers = register_and_token("ocr")
    image_buffer = io.BytesIO()
    Image.new("RGB", (1, 1), color="white").save(image_buffer, format="PNG")
    image = image_buffer.getvalue()
    response = client.post("/reports/upload", headers=headers, files={"upload": ("synthetic.png", image, "image/png")})
    assert response.status_code == 422
    assert "ocr is unavailable" in response.json()["detail"].lower()
    assert "success" not in response.json()["detail"].lower()


def test_unknown_tests_are_not_invented_and_missing_ranges_stay_missing():
    _, headers = register_and_token("unknown")
    response = upload_demo_pdf(headers, text="Synthetic/demo report\nUnknownMarker: 999 units")
    assert response.status_code == 201
    analysis = response.json()["analysis"]
    assert analysis["detected_tests"] == []
    assert any("No laboratory results" in line for line in analysis["important_observations"])


def test_explicit_reference_ranges_support_above_and_within_classification():
    _, headers = register_and_token("range")
    response = upload_demo_pdf(
        headers,
        text=(
            "Synthetic/demo report\n"
            "Hemoglobin: 14 g/dL Reference range: 12-16 g/dL\n"
            "Glucose: 110 mg/dL Reference range: 70-99 mg/dL"
        ),
    )
    assert response.status_code == 201
    values = {entry["test_name"]: entry for entry in response.json()["analysis"]["detected_tests"]}
    assert values["Hemoglobin"]["status"] == "WITHIN PROVIDED RANGE"
    assert values["Glucose"]["status"] == "ABOVE PROVIDED RANGE"


@pytest.mark.parametrize(
    ("text", "expected_value", "expected_unit", "expected_range", "expected_status"),
    [
        (
            "Hemoglobin\n10.2\ng/dL\nReference Range: 12 - 16 g/dL",
            "10.2", "g/dL", "12-16 g/dL", "BELOW PROVIDED RANGE",
        ),
        (
            "Glucose\n108\nmg/dL\nReference Range: 70-110 mg/dL",
            "108", "mg/dL", "70-110 mg/dL", "WITHIN PROVIDED RANGE",
        ),
        (
            "White Blood Cell Count: 7500 /uL\nReference Range: 4000-11000 /uL",
            "7500", "/uL", "4000-11000 /uL", "WITHIN PROVIDED RANGE",
        ),
    ],
)
def test_adjacent_line_values_units_and_ranges_are_associated(
    text, expected_value, expected_unit, expected_range, expected_status
):
    _, headers = register_and_token("adjacent")
    response = upload_demo_pdf(headers, text=f"Synthetic/demo report\n{text}")
    assert response.status_code == 201
    results = response.json()["analysis"]["detected_tests"]
    assert results
    result = results[0]
    assert result["value"] == expected_value
    assert result["unit"] == expected_unit
    assert result["reference_range"] == expected_range
    assert result["status"] == expected_status


def test_sequential_pdf_table_text_is_associated_by_test_rows():
    _, headers = register_and_token("table")
    table_text = (
        "Synthetic/demo table report\n"
        "Test\nResult\nUnit\nReference Range\n"
        "Hemoglobin\n10.2\ng/dL\n12-16 g/dL\n"
        "Glucose\n108\nmg/dL\n70-110 mg/dL"
    )
    response = upload_demo_pdf(headers, text=table_text)
    assert response.status_code == 201
    values = {entry["test_name"]: entry for entry in response.json()["analysis"]["detected_tests"]}
    assert values["Hemoglobin"]["value"] == "10.2"
    assert values["Hemoglobin"]["reference_range"] == "12-16 g/dL"
    assert values["Hemoglobin"]["status"] == "BELOW PROVIDED RANGE"
    assert values["Glucose"]["value"] == "108"
    assert values["Glucose"]["reference_range"] == "70-110 mg/dL"
    assert values["Glucose"]["status"] == "WITHIN PROVIDED RANGE"


def test_missing_value_has_no_status_and_administrative_numbers_are_ignored():
    _, headers = register_and_token("missingvalue")
    response = upload_demo_pdf(
        headers,
        text=(
            "Synthetic/demo report\n"
            "Report ID: 76543210\nDate: 2026-09-27\nPhone: 555-0100\n"
            "Hemoglobin\nReference Range: 12-16 g/dL"
        ),
    )
    assert response.status_code == 201
    results = response.json()["analysis"]["detected_tests"]
    hemoglobin = next(result for result in results if result["test_name"] == "Hemoglobin")
    assert hemoglobin["value"] is None
    assert hemoglobin["reference_range"] is None
    assert hemoglobin["status"] is None


def test_diagnosis_term_is_filtered_from_boilerplate_but_kept_as_report_content():
    _, headers = register_and_token("termcontext")
    boilerplate = upload_demo_pdf(
        headers,
        text="Synthetic demo report. This document is not for diagnosis. Hemoglobin: 13 g/dL",
    )
    assert boilerplate.status_code == 201
    boilerplate_terms = [term["term"].casefold() for term in boilerplate.json()["analysis"]["medical_terms"]]
    assert "diagnosis" not in boilerplate_terms

    clinical = upload_demo_pdf(headers, text="Diagnosis: Diagnosis is documented in the report.")
    assert clinical.status_code == 201
    clinical_terms = [term["term"].casefold() for term in clinical.json()["analysis"]["medical_terms"]]
    assert "diagnosis" in clinical_terms


def test_reference_range_column_heading_is_not_reported_as_a_medical_term():
    _, headers = register_and_token("rangeheading")
    response = upload_demo_pdf(
        headers,
        text="Synthetic/demo report\nHemoglobin: 10.2 g/dL\nReference Range: 12-16 g/dL",
    )
    assert response.status_code == 201
    terms = [term["term"].casefold() for term in response.json()["analysis"]["medical_terms"]]
    assert "reference range" not in terms


def test_report_lists_and_operations_are_owner_scoped():
    owner_email, owner_headers = register_and_token("owner")
    _, other_headers = register_and_token("other")
    uploaded = upload_demo_pdf(owner_headers)
    assert uploaded.status_code == 201
    report_id = uploaded.json()["id"]

    owner_list = client.get("/reports", headers=owner_headers)
    other_list = client.get("/reports", headers=other_headers)
    assert report_id in [entry["id"] for entry in owner_list.json()["reports"]]
    assert report_id not in [entry["id"] for entry in other_list.json()["reports"]]

    assert client.get(f"/reports/{report_id}", headers=other_headers).status_code == 404
    assert client.post(f"/reports/{report_id}/analyze", headers=other_headers).status_code == 404
    assert client.delete(f"/reports/{report_id}", headers=other_headers).status_code == 404
    assert client.get(f"/reports/{report_id}", headers=owner_headers).status_code == 200
    assert client.delete(f"/reports/{report_id}", headers=owner_headers).status_code == 204
    assert client.get(f"/reports/{report_id}", headers=owner_headers).status_code == 404

    with get_db() as connection:
        owner = connection.execute("SELECT id FROM users WHERE email = ?", (owner_email,)).fetchone()
        assert connection.execute("SELECT COUNT(*) FROM reports WHERE user_id = ?", (owner["id"],)).fetchone()[0] == 0


def test_malformed_persisted_summary_returns_a_safe_error():
    _, headers = register_and_token("malformed")
    uploaded = upload_demo_pdf(headers)
    report_id = uploaded.json()["id"]
    with get_db() as connection:
        connection.execute("UPDATE reports SET summary_text = ? WHERE id = ?", ("{broken-json", report_id))
    response = client.get(f"/reports/{report_id}", headers=headers)
    assert response.status_code == 500
    assert response.json()["detail"] == "The stored report summary could not be read safely."
    assert "Traceback" not in response.text
