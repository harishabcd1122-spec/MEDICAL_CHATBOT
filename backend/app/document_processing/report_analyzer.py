"""Conservative extraction for educational medical report summaries."""

import importlib.util
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

from backend.app.database.connection import get_db

DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 120
MAX_EXTRACTED_CHARACTERS = 1_000_000
REPORT_DISCLAIMER = (
    "This report explanation is for educational purposes only. It does not provide a diagnosis "
    "or replace professional medical advice. Laboratory results should be interpreted together "
    "with your symptoms, medical history, and the reference ranges provided by the testing laboratory."
)


class ReportProcessingError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def maximum_upload_bytes() -> int:
    configured = os.getenv("HEALTH_REPORT_MAX_UPLOAD_BYTES", str(DEFAULT_MAX_UPLOAD_BYTES))
    try:
        value = int(configured)
    except ValueError:
        return DEFAULT_MAX_UPLOAD_BYTES
    return value if value > 0 else DEFAULT_MAX_UPLOAD_BYTES


def _safe_display_filename(filename: str | None) -> str:
    candidate = (filename or "").replace("\\", "/").split("/")[-1]
    candidate = re.sub(r"[\x00-\x1f\x7f]", "", candidate).strip()
    return candidate[:180] or "Uploaded report"


def _validate_file(content: bytes, filename: str | None) -> tuple[str, str]:
    if not content:
        raise ReportProcessingError(422, "The uploaded file is empty.")
    if len(content) > maximum_upload_bytes():
        raise ReportProcessingError(413, "The report exceeds the configured upload size limit.")

    extension = Path(_safe_display_filename(filename)).suffix.lower()
    supported = {".pdf", ".png", ".jpg", ".jpeg"}
    if extension not in supported:
        raise ReportProcessingError(415, "Unsupported file type. Upload a PDF, PNG, JPG, or JPEG report.")

    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise ReportProcessingError(415, "The file contents do not match a PDF document.")
        return extension, "application/pdf"
    if extension == ".png":
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ReportProcessingError(415, "The file contents do not match a PNG image.")
        return extension, "image/png"
    if not content.startswith(b"\xff\xd8\xff"):
        raise ReportProcessingError(415, "The file contents do not match a JPEG image.")
    return extension, "image/jpeg"


def _ocr_available() -> bool:
    return bool(shutil.which("tesseract") and importlib.util.find_spec("pytesseract"))


def _extract_pdf_text(path: Path) -> tuple[str, int, str]:
    try:
        with path.open("rb") as file_handle:
            reader = PdfReader(file_handle, strict=True)
            if reader.is_encrypted:
                raise ReportProcessingError(422, "This PDF is password-protected and could not be read.")
            page_count = len(reader.pages)
            if page_count == 0:
                raise ReportProcessingError(422, "This PDF has no pages to read.")
            if page_count > MAX_PDF_PAGES:
                raise ReportProcessingError(413, "This PDF has too many pages to process safely.")
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except ReportProcessingError:
        raise
    except Exception as error:
        if error.__class__.__name__ in {"FileNotDecryptedError", "WrongPasswordError"}:
            raise ReportProcessingError(422, "This PDF is password-protected and could not be read.") from None
        raise ReportProcessingError(422, "This PDF is damaged or could not be read.") from None

    text = text[:MAX_EXTRACTED_CHARACTERS]
    if not text.strip() and _ocr_available() and importlib.util.find_spec("pdf2image"):
        try:
            from pdf2image import convert_from_path
            import pytesseract

            if page_count > 20:
                raise ReportProcessingError(413, "This scanned PDF has too many pages for local OCR processing.")
            images = convert_from_path(path, dpi=120, thread_count=1, timeout=30)
            text = "\n".join(pytesseract.image_to_string(image) for image in images)
        except ReportProcessingError:
            raise
        except Exception:
            raise ReportProcessingError(422, "Local OCR could not read this scanned PDF.") from None
        text = text[:MAX_EXTRACTED_CHARACTERS]
        if text.strip():
            return text, page_count, "local_ocr"
        raise ReportProcessingError(422, "No readable text was recognized in this scanned PDF.")
    if not text.strip():
        raise ReportProcessingError(
            422,
            "This PDF appears scanned or image-based. Local OCR is unavailable, so its contents could not be read automatically.",
        )
    return text, page_count, "pdf_text"


def _extract_image_text(path: Path) -> str:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image_format = image.format
            if image_format not in {"PNG", "JPEG"}:
                raise ReportProcessingError(415, "Unsupported image encoding. Upload a PNG or JPEG image.")
            if image.width * image.height > 40_000_000:
                raise ReportProcessingError(413, "This image is too large to process safely.")
            if not _ocr_available():
                raise ReportProcessingError(
                    422,
                    "The image is valid, but local OCR is unavailable. No report text was extracted.",
                )
            import pytesseract

            return pytesseract.image_to_string(image)[:MAX_EXTRACTED_CHARACTERS]
    except ReportProcessingError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ReportProcessingError(422, "This image is damaged or could not be read.") from None
    except Exception:
        raise ReportProcessingError(422, "Text could not be read from this image using local OCR.") from None


def _known_tests() -> list[dict[str, Any]]:
    with get_db() as connection:
        rows = connection.execute(
            "SELECT id, name, what_is_it, what_does_it_measure FROM lab_tests ORDER BY name"
        ).fetchall()
    return [dict(row) for row in rows]


def _known_terms() -> list[dict[str, Any]]:
    with get_db() as connection:
        rows = connection.execute(
            "SELECT id, term, category, simple_explanation, source FROM medical_terms ORDER BY term"
        ).fetchall()
    return [dict(row) for row in rows]


def _test_aliases(test: dict[str, Any]) -> list[tuple[str, str]]:
    test_id = test["id"]
    name = test["name"]
    aliases: list[tuple[str, str]] = [(name, name)]
    aliases.extend(((test_id.replace("-", " "), name), (test_id, name)))
    configured: dict[str, list[str]] = {
        "cbc": ["CBC", "complete blood count", "hemoglobin", "haemoglobin", "hematocrit", "haematocrit", "WBC", "white blood cell count", "white blood cells", "RBC", "red blood cells", "platelets"],
        "hba1c": ["HbA1c", "A1c", "glycated hemoglobin", "glycated haemoglobin"],
        "blood-glucose": ["glucose", "blood sugar", "fasting glucose", "fasting blood glucose"],
        "lipid-profile": ["lipid profile", "total cholesterol", "LDL", "HDL", "triglycerides"],
        "crp": ["CRP", "C-reactive protein"],
        "esr": ["ESR", "erythrocyte sedimentation rate"],
        "lft": ["LFT", "ALT", "AST", "bilirubin", "alkaline phosphatase", "ALP", "albumin"],
        "kft": ["KFT", "BUN", "eGFR"],
        "creatinine": ["creatinine"],
        "urea": ["urea", "blood urea nitrogen", "BUN"],
        "bilirubin": ["bilirubin", "total bilirubin", "direct bilirubin"],
    }
    canonical_names = {
        "hemoglobin": "Hemoglobin",
        "haemoglobin": "Hemoglobin",
        "hematocrit": "Hematocrit",
        "haematocrit": "Hematocrit",
        "wbc": "WBC",
        "white blood cell count": "White Blood Cell Count",
        "rbc": "RBC",
        "hba1c": "HbA1c",
        "a1c": "HbA1c",
        "crp": "CRP",
        "esr": "ESR",
        "ldl": "LDL",
        "hdl": "HDL",
        "alt": "ALT",
        "ast": "AST",
        "alp": "ALP",
        "bun": "BUN",
        "egfr": "eGFR",
    }
    aliases.extend((alias, canonical_names.get(alias.casefold(), alias[:1].upper() + alias[1:])) for alias in configured.get(test_id, []))
    unique: dict[str, tuple[str, str]] = {}
    for alias, display_name in aliases:
        if alias:
            unique[alias.casefold()] = (alias, display_name)
    return sorted(unique.values(), key=lambda value: len(value[0]), reverse=True)


_NUMBER_PATTERN = r"[<>]?\s*\d[\d,]*(?:\.\d+)?"
_UNIT_PATTERN = re.compile(
    r"(?:g\s*/\s*dL|mg\s*/\s*dL|g\s*/\s*L|mg\s*/\s*L|mmol\s*/\s*L|"
    r"(?:10\s*\^?\s*\d+\s*)?(?:/\s*[µμuU]L|cells\s*/\s*[µμuU]L|K\s*/\s*[µμuU]L)|"
    r"[µμuU]L|U\s*/\s*L|IU\s*/\s*L|ng\s*/\s*mL|pg\s*/\s*mL|"
    r"mm\s*/\s*hr|fL|%|mL\s*/\s*min(?:\s*/\s*1\.73\s*m\^?2)?)",
    re.IGNORECASE,
)
_RANGE_PATTERN = re.compile(
    rf"(?P<range>(?P<lower>{_NUMBER_PATTERN})\s*(?:-|–|—|\bto\b)\s*(?P<upper>{_NUMBER_PATTERN})|"
    rf"(?P<operator><=|>=|<|>)\s*(?P<bound>{_NUMBER_PATTERN}))",
    re.IGNORECASE,
)
_RANGE_MARKER = re.compile(r"(?:reference|ref\.?|normal)\s+range\s*[:=]?\s*|\brange\s*[:=]\s*", re.IGNORECASE)


def _parse_range_candidate(text: str) -> tuple[str | None, float | None, float | None]:
    candidate = text.strip().strip(":=()[] ")
    if not candidate or re.search(r"\b\d{4}-\d{1,2}-\d{1,2}\b", candidate):
        return None, None, None
    match = _RANGE_PATTERN.match(candidate)
    if match is None:
        return None, None, None
    unit_match = _UNIT_PATTERN.match(candidate[match.end():].lstrip())
    if unit_match is None:
        return None, None, None
    unit = unit_match.group(0).strip()
    range_label = match.group("range").replace("–", "-").replace("—", "-")
    range_label = re.sub(r"\s+to\s+", "-", range_label, flags=re.IGNORECASE)
    normalized_range = f"{range_label} {unit}"
    if match.group("lower") is not None:
        lower = float(match.group("lower").replace(",", "").replace(" ", ""))
        upper = float(match.group("upper").replace(",", "").replace(" ", ""))
        return normalized_range, lower, upper
    bound_value = float(match.group("bound").replace(",", "").replace(" ", "").lstrip("<>"))
    operator = match.group("operator")
    return normalized_range, (bound_value if operator.startswith(">") else None), (bound_value if operator.startswith("<") else None)


def _parse_associated_value(following_text: str) -> dict[str, Any] | None:
    """Parse value/unit/range from contiguous text immediately after a recognized test label."""
    lines = [line.strip() for line in following_text[:240].splitlines() if line.strip()]
    header_lines = {"result", "value", "unit", "reference range", "ref range", "normal range"}
    value_match = None
    value_line_index = -1
    for index, line in enumerate(lines[:3]):
        if line.casefold().rstrip(":") in header_lines:
            continue
        value_match = re.match(rf"^\s*[:=]?\s*(?P<value>{_NUMBER_PATTERN})(?P<tail>.*)$", line)
        if value_match is None:
            return None
        value_line_index = index
        break
    if value_match is None:
        return None

    raw_value = value_match.group("value").replace(",", "").replace(" ", "")
    if raw_value.startswith(("<", ">")):
        return None
    digits = re.sub(r"\D", "", raw_value)
    if not digits or len(digits) > 7:
        return None
    try:
        numeric_value = float(raw_value)
    except ValueError:
        return None

    value_tail = value_match.group("tail").strip()
    unit_match = _UNIT_PATTERN.search(value_tail)
    unit_line_index = value_line_index
    unit_end = -1
    after_unit = ""
    if unit_match is not None:
        unit = unit_match.group(0).strip()
        unit_end = unit_match.end()
        after_unit = value_tail[unit_end:].strip()
    elif value_line_index + 1 < len(lines):
        next_line = lines[value_line_index + 1]
        unit_match = _UNIT_PATTERN.match(next_line)
        if unit_match is None:
            return None
        unit = unit_match.group(0).strip()
        unit_line_index += 1
        unit_end = unit_match.end()
        after_unit = next_line[unit_end:].strip()
    else:
        return None

    range_lines = []
    if after_unit:
        range_lines.append(after_unit)
    range_lines.extend(lines[unit_line_index + 1:unit_line_index + 4])
    reference = None
    low = high = None
    pending_range_marker = False
    for line in range_lines:
        marker = _RANGE_MARKER.search(line)
        if marker:
            candidate = line[marker.end():].strip()
            pending_range_marker = not candidate
            if candidate:
                reference, low, high = _parse_range_candidate(candidate)
                if reference:
                    break
            continue
        if pending_range_marker:
            reference, low, high = _parse_range_candidate(line)
            pending_range_marker = False
            if reference:
                break
            continue
        reference, low, high = _parse_range_candidate(line)
        if reference:
            break

    if reference is None:
        status = "REFERENCE RANGE NOT PROVIDED"
    elif low is not None and numeric_value < low:
        status = "BELOW PROVIDED RANGE"
    elif high is not None and numeric_value > high:
        status = "ABOVE PROVIDED RANGE"
    else:
        status = "WITHIN PROVIDED RANGE"
    return {"value": raw_value, "unit": unit, "reference_range": reference, "status": status}


def _normalized_text_for_matching(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    text = re.sub(r"(?<=\d)\s*[-–—]\s*(?=\d)", "-", text)
    return text


def _extract_lab_results(text: str, tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    searchable = _normalized_text_for_matching(text)
    candidates: list[tuple[int, int, str, str, dict[str, Any]]] = []
    for test in tests:
        for alias, display_name in _test_aliases(test):
            label_pattern = re.compile(rf"(?<![\w]){re.escape(alias)}(?![\w])", re.IGNORECASE)
            for match in label_pattern.finditer(searchable):
                candidates.append((match.start(), match.end(), test["id"], display_name, test))

    candidates.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    labels: list[tuple[int, int, str, str, dict[str, Any]]] = []
    seen_labels: set[tuple[int, str, str]] = set()
    for candidate in candidates:
        key = (candidate[0], candidate[2], candidate[3].casefold())
        if key in seen_labels:
            continue
        seen_labels.add(key)
        labels.append(candidate)
    labels.sort(key=lambda item: item[0])

    detected: dict[tuple[str, str], dict[str, Any]] = {}
    for index, (start, end, test_id, display_name, test) in enumerate(labels):
        next_start = labels[index + 1][0] if index + 1 < len(labels) else min(len(searchable), end + 180)
        association_window = searchable[end:next_start]
        key = (test_id, display_name.casefold())
        result = _parse_associated_value(association_window)
        current = detected.get(key)
        if current is None:
            current = {
                "test_id": test_id,
                "test_name": display_name,
                "value": None,
                "unit": None,
                "reference_range": None,
                "status": None,
                "knowledge_description": test.get("what_is_it") or "",
            }
            detected[key] = current
        if result and (current["value"] is None or result["reference_range"]):
            result.pop("_range_match", None)
            current.update(result)
    return list(detected.values())


_BOILERPLATE_CONTEXT = re.compile(
    r"\b(?:synthetic(?:\s*/\s*demo)?\s+(?:test\s+)?report|demo\s+report|"
    r"not\s+(?:for\s+)?diagnosis|not\s+a\s+diagnosis|does\s+not\s+(?:provide|constitute)\s+(?:a\s+)?diagnosis|"
    r"educational\s+purposes|medical\s+disclaimer|report\s+id|patient\s+id|page\s+\d+|"
    r"source\s*:|generated\s+by\s+healthbridge)\b",
    re.IGNORECASE,
)


def _is_meaningful_term_occurrence(text: str, match: re.Match[str], term_name: str) -> bool:
    left = max(text.rfind("\n", 0, match.start()), text.rfind(".", 0, match.start())) + 1
    line_end = text.find("\n", match.end())
    sentence_end = text.find(".", match.end())
    ends = [position for position in (line_end, sentence_end) if position >= 0]
    right = min(ends) if ends else len(text)
    context = text[left:right].strip()
    if term_name.casefold() == "diagnosis" and re.match(r"diagnosis\s*:", context, re.IGNORECASE):
        return True
    if term_name.casefold() == "reference range" and re.match(r"reference\s+range\s*[:=]", context, re.IGNORECASE):
        return False
    return _BOILERPLATE_CONTEXT.search(context) is None


def analyze_extracted_text(
    text: str,
    filename: str,
    media_type: str,
    page_count: int | None,
    extraction_method: str,
) -> dict[str, Any]:
    tests = _known_tests()
    terms = _known_terms()
    detected_terms: list[dict[str, Any]] = []
    normalized_text = text.casefold()
    for term in terms:
        name = term["term"]
        occurrences = list(re.finditer(rf"(?<![\w]){re.escape(name)}(?![\w])", normalized_text, re.IGNORECASE))
        if any(_is_meaningful_term_occurrence(text, match, name) for match in occurrences):
            detected_terms.append({
                "term": name,
                "simple_explanation": term.get("simple_explanation") or "",
                "category": term.get("category"),
                "source": term.get("source"),
            })

    lab_results = _extract_lab_results(text, tests)
    observations: list[str] = []
    questions: list[str] = []
    for result in lab_results:
        name = result["test_name"]
        if result["status"] == "BELOW PROVIDED RANGE":
            observations.append(f"The reported {name} value is below the reference range provided in the report.")
            questions.append("What could explain this result?")
        elif result["status"] == "ABOVE PROVIDED RANGE":
            observations.append(f"The reported {name} value is above the reference range provided in the report.")
            questions.append("What could explain this result?")
        elif result["status"] == "WITHIN PROVIDED RANGE":
            observations.append(f"The reported {name} value is within the reference range provided in the report.")
        elif result["value"] is not None:
            observations.append(f"A value was read for {name}; a reference range was not provided in the uploaded report.")
            questions.append("How should this result be interpreted when the report does not show a reference range?")
        else:
            observations.append(f"{name} was mentioned, but a value was not clearly detected.")
            questions.append("Could you review the reported result and confirm its value and units?")

    if not questions and lab_results:
        questions.extend(["How do these results relate to my symptoms and medical history?", "Should any test be repeated?"])
    if not lab_results:
        observations.append("No laboratory results from the current test knowledge base were confidently detected in readable text.")
        questions.extend(["Could you review this report with me?", "Are any additional tests appropriate for my situation?"])
    questions = list(dict.fromkeys(questions))[:5]

    return {
        "document": {
            "filename": filename,
            "media_type": media_type,
            "page_count": page_count,
            "extraction_method": extraction_method,
            "readable_text": True,
        },
        "summary": (
            f"The document was read and {len(lab_results)} result entr{'y' if len(lab_results) == 1 else 'ies'} "
            f"matched the supported laboratory test knowledge base. This is an extraction summary, not a diagnosis."
        ),
        "detected_tests": lab_results,
        "medical_terms": detected_terms,
        "important_observations": observations,
        "questions_for_healthcare_professional": questions,
        "disclaimer": REPORT_DISCLAIMER,
    }


def process_report(content: bytes, filename: str | None) -> tuple[dict[str, Any], str, str]:
    extension, media_type = _validate_file(content, filename)
    safe_name = _safe_display_filename(filename)
    with tempfile.TemporaryDirectory(prefix="healthbridge-report-") as temp_dir:
        temporary_path = Path(temp_dir) / f"{uuid4().hex}{extension}"
        temporary_path.write_bytes(content)
        if extension == ".pdf":
            text, page_count, extraction_method = _extract_pdf_text(temporary_path)
        else:
            text = _extract_image_text(temporary_path)
            page_count = 1
            extraction_method = "local_ocr"
            if not text.strip():
                raise ReportProcessingError(422, "No readable text was found in this image.")

    analysis = analyze_extracted_text(text, safe_name, media_type, page_count, extraction_method)
    return analysis, safe_name, media_type