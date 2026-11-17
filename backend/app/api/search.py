"""
HealthBridge AI - Global Search API Endpoint
Searches verified database entries across diseases, medical terms, and laboratory tests.
Returns structured categorised results with zero fabricated entities.
"""

from fastapi import APIRouter, Query
from typing import Dict, Any, List
import json
from backend.app.database.connection import get_db

router = APIRouter(prefix="/search", tags=["Global Search"])

@router.get("")
def global_search(q: str = Query(..., min_length=2, description="Search query")):
    query_str = f"%{q.strip().lower()}%"
    results: Dict[str, List[Any]] = {
        "diseases": [],
        "medical_terms": [],
        "lab_tests": []
    }

    with get_db() as conn:
        cursor = conn.cursor()

        # Diseases
        cursor.execute("""
        SELECT id, name, simple_definition, common_symptoms FROM diseases
        WHERE LOWER(name) LIKE ? OR LOWER(simple_definition) LIKE ? OR LOWER(common_symptoms) LIKE ?
        LIMIT 5
        """, (query_str, query_str, query_str))
        for row in cursor.fetchall():
            d = dict(row)
            try:
                d["common_symptoms"] = json.loads(d["common_symptoms"])
            except Exception:
                d["common_symptoms"] = []
            results["diseases"].append(d)

        # Medical Terms
        cursor.execute("""
        SELECT id, term, category, simple_explanation, very_simple_explanation, tamil_explanation, hindi_explanation 
        FROM medical_terms
        WHERE LOWER(term) LIKE ? OR LOWER(simple_explanation) LIKE ? OR LOWER(related_terms) LIKE ?
        LIMIT 6
        """, (query_str, query_str, query_str))
        for row in cursor.fetchall():
            results["medical_terms"].append(dict(row))

        # Lab Tests
        cursor.execute("""
        SELECT id, name, what_is_it, what_does_it_measure FROM lab_tests
        WHERE LOWER(name) LIKE ? OR LOWER(what_is_it) LIKE ? OR LOWER(what_does_it_measure) LIKE ?
        LIMIT 5
        """, (query_str, query_str, query_str))
        for row in cursor.fetchall():
            results["lab_tests"].append(dict(row))

    total_count = len(results["diseases"]) + len(results["medical_terms"]) + len(results["lab_tests"])
    return {
        "query": q,
        "total_results": total_count,
        "results": results
    }
