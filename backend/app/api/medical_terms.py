"""
HealthBridge AI - Medical Terminology Simplifier API Endpoints
Medical terms with simple English, very simple, Tamil, and Hindi explanations.
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
import json
from backend.app.database.connection import get_db
from backend.app.schemas.knowledge import MedicalTermItem

router = APIRouter(prefix="/medical-terms", tags=["Medical Terminology"])

def parse_term_row(row) -> dict:
    d = dict(row)
    if d.get("related_terms"):
        try:
            d["related_terms"] = json.loads(d["related_terms"])
        except Exception:
            d["related_terms"] = []
    else:
        d["related_terms"] = []
    return d

@router.get("", response_model=List[MedicalTermItem])
def list_terms(
    q: Optional[str] = Query(None, description="Search term"),
    category: Optional[str] = Query(None, description="Category filter (Blood, Heart, Respiratory, Laboratory, General, Medicine)")
):
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM medical_terms WHERE 1=1"
        params = []

        if category:
            query += " AND LOWER(category) = ?"
            params.append(category.strip().lower())

        if q:
            term = f"%{q.strip().lower()}%"
            query += " AND (LOWER(term) LIKE ? OR LOWER(simple_explanation) LIKE ? OR LOWER(tamil_explanation) LIKE ? OR LOWER(hindi_explanation) LIKE ?)"
            params.extend([term, term, term, term])

        query += " ORDER BY term ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [parse_term_row(r) for r in rows]

@router.get("/{term_id}", response_model=MedicalTermItem)
def get_term(term_id: str):
    clean_id = term_id.strip().lower()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM medical_terms 
        WHERE LOWER(id) = ? OR LOWER(term) = ?
        """, (clean_id, clean_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="I don't have enough reliable information to answer that safely."
            )
        return parse_term_row(row)
