"""
HealthBridge AI - Prototype ML Evaluation Endpoint
Provides verified training metrics, model comparisons, and confusion matrices.
Explicitly clarifies that prototype scores do not represent clinical diagnostic accuracy.
"""

from fastapi import APIRouter, HTTPException
import json
import os

router = APIRouter(prefix="/ml", tags=["ML Evaluation"])

EVAL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "evaluation", "metrics.json")

@router.get("/evaluation")
def get_evaluation_metrics():
    if not os.path.exists(EVAL_PATH):
        raise HTTPException(
            status_code=500,
            detail="Evaluation metrics not generated yet. Run ML training pipeline."
        )

    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    return {
        "title": "Prototype ML Evaluation",
        "notice": "Model performance on a dataset does not represent clinical diagnostic accuracy.",
        "data": metrics
    }
