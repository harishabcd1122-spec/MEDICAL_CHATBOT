"""
HealthBridge AI - Prototype ML Model Inference Service
Computes Model Match Scores for supported conditions.
Strictly separates prototype classification scores from clinical diagnostic certainty.
"""

from typing import Dict, Any, List, Optional
import os
import joblib
import pandas as pd
from backend.app.safety.disclaimer import MODEL_SCORE_NOTE, GLOBAL_DISCLAIMER_EN

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "models", "best_model.joblib")

_model_bundle = None

def get_model_bundle():
    global _model_bundle
    if _model_bundle is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Run training pipeline first.")
        _model_bundle = joblib.load(MODEL_PATH)
    return _model_bundle

def predict_conditions(feature_vector: Dict[str, int], top_k: int = 3) -> Dict[str, Any]:
    """
    Runs model inference on the normalized symptom feature vector.
    Calculates Model Match Score for supported conditions.
    """
    bundle = get_model_bundle()
    model = bundle["model"]
    feature_names = bundle["features"]
    classes = bundle["classes"]

    # Construct single-row DataFrame aligned with training columns
    row_data = {feat: [feature_vector.get(feat, 0)] for feat in feature_names}
    df_input = pd.DataFrame(row_data)

    active_symptoms_count = sum(feature_vector.get(f, 0) for f in feature_names)

    # Uncertainty handling: Insufficient symptoms
    if active_symptoms_count < 1:
        return {
            "status": "insufficient_information",
            "possible_conditions": [],
            "message": (
                "I don't have enough reliable information to provide a useful prototype assessment. "
                "You may provide additional details such as symptom duration and other symptoms, "
                "or consult a healthcare professional."
            ),
            "disclaimer_note": MODEL_SCORE_NOTE
        }

    # Model probability distribution
    probabilities = model.predict_proba(df_input)[0]

    # Pair each condition with its score
    condition_scores = []
    for cls_name, prob in zip(classes, probabilities):
        score_val = float(prob)
        condition_scores.append({
            "condition": cls_name,
            "raw_score": score_val,
            "model_match_score": round(score_val * 100, 1),
            "score_display": f"{round(score_val * 100, 1)}%"
        })

    # Sort descending
    condition_scores.sort(key=lambda x: x["raw_score"], reverse=True)
    top_matches = condition_scores[:top_k]
    highest_score = top_matches[0]["raw_score"]

    # Uncertainty handling: Outside supported set if highest match score is very low
    if highest_score < 0.20:
        return {
            "status": "out_of_scope",
            "possible_conditions": [],
            "message": (
                "This symptom combination is outside the current prototype's supported disease set. "
                "Please consult a healthcare professional for appropriate evaluation."
            ),
            "disclaimer_note": MODEL_SCORE_NOTE
        }

    # Meaningful matches
    filtered_matches = [m for m in top_matches if m["raw_score"] >= 0.15]
    if not filtered_matches:
        filtered_matches = [top_matches[0]]

    top_condition_name = filtered_matches[0]["condition"]

    return {
        "status": "success",
        "top_condition": top_condition_name,
        "possible_conditions": filtered_matches,
        "model_name": bundle["model_name"],
        "explanation": (
            "The symptoms entered can occur in several conditions. "
            "The model output is an AI-assisted informational assessment and does not confirm a diagnosis."
        ),
        "score_note": MODEL_SCORE_NOTE,
        "disclaimer": GLOBAL_DISCLAIMER_EN
    }
