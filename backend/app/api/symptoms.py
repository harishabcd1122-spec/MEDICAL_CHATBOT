"""
HealthBridge AI - Symptom Analysis API Endpoint
Controlled hybrid architecture: Input -> Emergency Screen -> Normalization -> ML -> Model Match Score -> Urgency Engine -> Doctor Questions -> Disclaimer.
"""

from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.symptoms import SymptomAnalyzeRequest, SymptomAnalyzeResponse
from backend.app.safety.emergency_engine import check_emergency
from backend.app.safety.urgency_engine import evaluate_urgency, generate_doctor_questions
from backend.app.safety.disclaimer import get_disclaimer, MODEL_SCORE_NOTE
from backend.app.ml.symptom_normalizer import normalize_symptoms
from backend.app.ml.inference import predict_conditions

router = APIRouter(prefix="/symptoms", tags=["Symptom Analysis"])

@router.post("/analyze", response_model=SymptomAnalyzeResponse)
def analyze_symptoms(req: SymptomAnalyzeRequest):
    user_input = req.symptoms.strip()
    lang = req.language or "en"

    # Step 1: Pre-AI Rule-Based Emergency Safety Screen
    emergency_eval = check_emergency(user_input)
    if emergency_eval["is_emergency"]:
        # Immediately surface emergency triage card overriding normal chatbot / ML response
        return {
            "status": "emergency_detected",
            "raw_input": user_input,
            "detected_language": lang,
            "is_emergency": True,
            "emergency_details": emergency_eval,
            "extracted_symptoms": [],
            "possible_conditions": [],
            "urgency": {
                "urgency_level": "URGENT",
                "badge_color": "red",
                "level_note": "Emergency safety screening has highest priority over general responses.",
                "explanation": emergency_eval["message"],
                "urgent_symptoms_flagged": emergency_eval["matched_categories"],
                "questions_for_doctor": [
                    "What immediate emergency stabilization is being administered?",
                    "Are urgent cardiac or pulmonary diagnostic tests required right now?"
                ]
            },
            "explanation": emergency_eval["message"],
            "score_note": None,
            "questions_for_doctor": [],
            "disclaimer": get_disclaimer(lang)
        }

    # Step 2: Multilingual Symptom Extraction & Normalization
    norm_result = normalize_symptoms(user_input)
    detected_lang = norm_result["detected_language"]
    extracted_syms = norm_result["extracted_symptoms"]
    feature_vec = norm_result["feature_vector"]

    # Step 3: Check feature sufficiency
    if not norm_result["is_sufficient"]:
        return {
            "status": "insufficient_information",
            "raw_input": user_input,
            "detected_language": detected_lang,
            "is_emergency": False,
            "emergency_details": None,
            "extracted_symptoms": [],
            "possible_conditions": [],
            "urgency": {
                "urgency_level": "LOW",
                "badge_color": "green",
                "level_note": "Urgency/Safety Level refers to safety and triage indicators.",
                "explanation": "No specific symptoms could be recognized from the input.",
                "urgent_symptoms_flagged": [],
                "questions_for_doctor": []
            },
            "explanation": (
                "I don't have enough reliable information to provide a useful prototype assessment. "
                "You may provide additional details such as symptom duration and other symptoms, "
                "or consult a healthcare professional."
            ),
            "score_note": MODEL_SCORE_NOTE,
            "questions_for_doctor": [
                "What symptoms should I keep a record of before visiting the clinic?",
                "When is the right time to seek a medical consultation for unclear symptoms?"
            ],
            "disclaimer": get_disclaimer(detected_lang)
        }

    # Step 4: ML Inference & Model Match Score
    prediction = predict_conditions(feature_vec, top_k=3)

    if prediction["status"] == "out_of_scope":
        return {
            "status": "out_of_scope",
            "raw_input": user_input,
            "detected_language": detected_lang,
            "is_emergency": False,
            "emergency_details": None,
            "extracted_symptoms": extracted_syms,
            "possible_conditions": [],
            "urgency": {
                "urgency_level": "MODERATE",
                "badge_color": "yellow",
                "level_note": "Urgency/Safety Level refers to safety and triage indicators.",
                "explanation": "The symptom pattern does not match the prototype's 20-condition benchmark dataset.",
                "urgent_symptoms_flagged": [],
                "questions_for_doctor": [
                    "What clinical evaluations are recommended for my specific symptoms?"
                ]
            },
            "explanation": (
                "This symptom combination is outside the current prototype's supported disease set. "
                "Please consult a healthcare professional for appropriate evaluation."
            ),
            "score_note": MODEL_SCORE_NOTE,
            "questions_for_doctor": [
                "Could these symptoms point to a condition outside common outpatient infections?",
                "Are specialized examinations or lab tests recommended?"
            ],
            "disclaimer": get_disclaimer(detected_lang)
        }

    top_condition = prediction.get("top_condition", "")
    possible_conditions = prediction.get("possible_conditions", [])

    # Step 5: Urgency & Safety Engine Triage Evaluation
    urgency_res = evaluate_urgency(extracted_syms, user_input, top_condition)

    return {
        "status": "success",
        "raw_input": user_input,
        "detected_language": detected_lang,
        "is_emergency": False,
        "emergency_details": None,
        "extracted_symptoms": extracted_syms,
        "possible_conditions": possible_conditions,
        "urgency": urgency_res,
        "explanation": (
            "The symptoms entered can occur in several conditions. "
            "The model output is an AI-assisted informational assessment and does not confirm a diagnosis."
        ),
        "score_note": MODEL_SCORE_NOTE,
        "questions_for_doctor": urgency_res["questions_for_doctor"],
        "disclaimer": get_disclaimer(detected_lang)
    }
