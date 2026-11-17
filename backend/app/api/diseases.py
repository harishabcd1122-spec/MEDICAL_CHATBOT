"""
HealthBridge AI - Disease Knowledge Base API Endpoints
Verified disease information, definitions, warning signs, and doctor questions.
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
import json
from backend.app.database.connection import get_db
from backend.app.schemas.knowledge import DiseaseItem

router = APIRouter(prefix="/diseases", tags=["Disease Knowledge Base"])

def parse_row(row) -> dict:
    d = dict(row)
    for field in ["common_symptoms", "possible_causes", "risk_factors", "general_prevention",
                  "common_diagnostic_tests", "faqs", "related_medical_terms"]:
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except Exception:
                d[field] = []
        else:
            d[field] = []
    return d

@router.get("", response_model=List[DiseaseItem])
def list_diseases(q: Optional[str] = Query(None, description="Search term for disease name or symptoms")):
    with get_db() as conn:
        cursor = conn.cursor()
        if q:
            term = f"%{q.strip().lower()}%"
            cursor.execute("""
            SELECT * FROM diseases 
            WHERE LOWER(name) LIKE ? OR LOWER(simple_definition) LIKE ? OR LOWER(common_symptoms) LIKE ?
            ORDER BY name ASC
            """, (term, term, term))
        else:
            cursor.execute("SELECT * FROM diseases ORDER BY name ASC")
        rows = cursor.fetchall()
        return [parse_row(r) for r in rows]

@router.get("/{disease_id}", response_model=DiseaseItem)
def get_disease(disease_id: str):
    clean_id = disease_id.strip().lower()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM diseases WHERE LOWER(id) = ? OR LOWER(name) = ?", (clean_id, clean_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This condition is outside the current prototype's supported disease set."
            )
        return parse_row(row)
