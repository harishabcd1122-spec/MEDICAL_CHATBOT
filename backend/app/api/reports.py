"""Authenticated medical report upload and structured extraction endpoints."""

import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from backend.app.database.connection import get_db
from backend.app.document_processing.report_analyzer import ReportProcessingError, process_report, maximum_upload_bytes
from backend.app.utils.security import get_current_user

router = APIRouter(prefix="/reports", tags=["Medical Reports"])


def _owned_report(report_id: int, user_id: int):
    with get_db() as connection:
        row = connection.execute(
            "SELECT id, user_id, original_filename, secure_filename, file_type, upload_date, summary_text, status "
            "FROM reports WHERE id = ? AND user_id = ?",
            (report_id, user_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Report not found.")
        values = connection.execute(
            "SELECT test_name, result_value, reference_range, status FROM report_values "
            "WHERE report_id = ? ORDER BY id",
            (report_id,),
        ).fetchall()
    try:
        analysis = json.loads(row["summary_text"] or "{}")
        if not isinstance(analysis, dict):
            raise ValueError("Stored report structure is invalid")
    except (TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="The stored report summary could not be read safely.") from None

    return {
        "id": row["id"],
        "filename": row["original_filename"],
        "file_type": row["file_type"],
        "uploaded_at": row["upload_date"],
        "status": row["status"],
        "analysis": analysis,
        "lab_values": [dict(value) for value in values],
    }


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_report(
    upload: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    try:
        content = await upload.read(maximum_upload_bytes() + 1)
        analysis, safe_filename, media_type = process_report(content, upload.filename)
    except ReportProcessingError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    except Exception:
        raise HTTPException(status_code=500, detail="The report could not be processed safely.") from None
    finally:
        await upload.close()

    user_id = int(current_user["id"])
    secure_identifier = f"{uuid4().hex}{Path(safe_filename).suffix.lower()}"
    try:
        with get_db() as connection:
            cursor = connection.execute(
                "INSERT INTO reports (user_id, original_filename, secure_filename, file_type, summary_text, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, safe_filename, secure_identifier, media_type, json.dumps(analysis), "completed"),
            )
            report_id = cursor.lastrowid
            for result in analysis["detected_tests"]:
                value_text = ""
                if result.get("value") is not None:
                    value_text = str(result["value"])
                    if result.get("unit"):
                        value_text += f" {result['unit']}"
                connection.execute(
                    "INSERT INTO report_values (report_id, test_name, result_value, reference_range, status) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (report_id, result["test_name"], value_text, result.get("reference_range"), result["status"]),
                )
    except Exception:
        raise HTTPException(status_code=500, detail="The report summary could not be saved safely.") from None

    return _owned_report(int(report_id), user_id)


@router.get("")
def list_reports(current_user: dict = Depends(get_current_user)):
    try:
        with get_db() as connection:
            rows = connection.execute(
                "SELECT id, original_filename, file_type, upload_date, status, summary_text "
                "FROM reports WHERE user_id = ? ORDER BY upload_date DESC, id DESC",
                (int(current_user["id"]),),
            ).fetchall()
        results = []
        for row in rows:
            try:
                analysis = json.loads(row["summary_text"] or "{}")
                summary = analysis.get("summary", "Report summary is unavailable.") if isinstance(analysis, dict) else "Report summary is unavailable."
            except (TypeError, ValueError, json.JSONDecodeError):
                summary = "Report summary is unavailable."
            results.append({
                "id": row["id"],
                "filename": row["original_filename"],
                "file_type": row["file_type"],
                "uploaded_at": row["upload_date"],
                "status": row["status"],
                "summary": summary,
            })
        return {"reports": results}
    except Exception:
        raise HTTPException(status_code=500, detail="Reports could not be loaded safely.") from None


@router.get("/{report_id}")
def get_report(report_id: int, current_user: dict = Depends(get_current_user)):
    return _owned_report(report_id, int(current_user["id"]))


@router.post("/{report_id}/analyze")
def analyze_report(report_id: int, current_user: dict = Depends(get_current_user)):
    return _owned_report(report_id, int(current_user["id"]))


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: int, current_user: dict = Depends(get_current_user)):
    try:
        with get_db() as connection:
            cursor = connection.execute(
                "DELETE FROM reports WHERE id = ? AND user_id = ?",
                (report_id, int(current_user["id"])),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Report not found.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="The report could not be deleted safely.") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)