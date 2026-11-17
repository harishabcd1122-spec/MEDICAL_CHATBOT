"""
HealthBridge AI - Laboratory Test Explainer API Endpoints
Plain-language explanations of diagnostic lab tests without isolated diagnosis.
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from backend.app.database.connection import get_db
from backend.app.schemas.knowledge import LabTestItem

router = APIRouter(prefix="/lab-tests", tags=["Laboratory Tests"])

@router.get("", response_model=List[LabTestItem])
def list_lab_tests(q: Optional[str] = Query(None, description="Search term")):
    with get_db() as conn:
        cursor = conn.cursor()
        if q:
            term = f"%{q.strip().lower()}%"
            cursor.execute("""
            SELECT * FROM lab_tests 
            WHERE LOWER(name) LIKE ? OR LOWER(what_is_it) LIKE ? OR LOWER(what_does_it_measure) LIKE ?
            ORDER BY name ASC
            """, (term, term, term))
        else:
            cursor.execute("SELECT * FROM lab_tests ORDER BY name ASC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@router.get("/{test_id}", response_model=LabTestItem)
def get_lab_test(test_id: str):
    clean_id = test_id.strip().lower()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lab_tests WHERE LOWER(id) = ? OR LOWER(name) = ?", (clean_id, clean_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="I don't have enough reliable information to answer that safely."
            )
        return dict(row)
