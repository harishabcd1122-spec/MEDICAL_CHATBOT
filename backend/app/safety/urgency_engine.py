"""
HealthBridge AI - Urgency & Safety Triage Engine
Evaluates symptom combinations and sets Urgency/Safety Level:
LOW, MODERATE, or URGENT.
Generates relevant questions for doctor consultations.
"""

from typing import Dict, Any, List

def evaluate_urgency(
    extracted_symptoms: List[str],
    raw_text: str = "",
    top_condition: str = ""
) -> Dict[str, Any]:
    """
    Evaluates safety triage indicators.
    Urgency/Safety Level refers to safety and triage indicators.
    It does NOT represent the probability of having a disease.
    """
    symptoms_set = set(extracted_symptoms)

    # Urgent indicators
    urgent_symptoms = {
        "shortness_of_breath", "chest_pain", "cough_with_blood", "high_fever"
    }

    # Moderate indicators (persistent, infectious or systemic)
    moderate_symptoms = {
        "fever", "vomiting", "diarrhea", "severe_headache", "throbbing_headache",
        "abdominal_pain", "wheezing", "burning_urination", "unexplained_weight_loss",
        "skin_rash", "red_spots_blisters"
    }

    urgent_matches = list(symptoms_set.intersection(urgent_symptoms))
    moderate_matches = list(symptoms_set.intersection(moderate_symptoms))

    if len(urgent_matches) >= 2 or ("chest_pain" in urgent_matches and "shortness_of_breath" in urgent_matches):
        level = "URGENT"
        badge_color = "red"
        explanation = (
            "Potential high-urgency indicators detected (e.g., chest pain, respiratory symptoms, or high fever). "
            "Prompt professional medical evaluation is strongly recommended."
        )
    elif len(urgent_matches) >= 1 or len(moderate_matches) >= 2 or top_condition in ["Pneumonia", "Dengue", "Malaria", "Typhoid", "COVID-19"]:
        level = "MODERATE"
        badge_color = "yellow"
        explanation = (
            "The reported symptoms may warrant professional medical evaluation depending on duration, "
            "severity, and individual medical history."
        )
    else:
        level = "LOW"
        badge_color = "green"
        explanation = (
            "No immediate emergency indicators detected from the entered symptoms. "
            "Self-monitoring and routine healthcare consultation are advised if symptoms persist."
        )

    # Doctor consultation questions tailored to the symptoms
    questions = generate_doctor_questions(extracted_symptoms, top_condition)

    return {
        "urgency_level": level,
        "badge_color": badge_color,
        "level_note": "Urgency/Safety Level refers to safety and triage indicators. It does not represent the probability of having a disease.",
        "explanation": explanation,
        "urgent_symptoms_flagged": urgent_matches,
        "questions_for_doctor": questions
    }

def generate_doctor_questions(extracted_symptoms: List[str], condition_hint: str = "") -> List[str]:
    """
    Provides relevant questions the user may ask a qualified doctor.
    """
    questions = [
        "What could these symptoms indicate based on my full medical history?",
        "Are there any specific warning signs or red flags I should monitor?",
        "What diagnostic tests or laboratory investigations, if any, are appropriate?"
    ]

    syms = set(extracted_symptoms)
    if "fever" in syms or "high_fever" in syms or "chills" in syms:
        questions.append("If the fever persists beyond 3 days, should a Complete Blood Count (CBC) or fever panel be done?")
    if "cough" in syms or "shortness_of_breath" in syms or "chest_pain" in syms:
        questions.append("Would a chest examination or oxygen saturation (SpO2) check be recommended?")
    if "burning_urination" in syms or "pelvic_discomfort" in syms:
        questions.append("Is a urine routine examination or culture needed to check for infection?")
    if "abdominal_pain" in syms or "stomach_burning" in syms or "acid_reflux" in syms:
        questions.append("Are these digestive symptoms related to gastritis, reflux, or dietary factors?")
    if "skin_rash" in syms or "red_spots_blisters" in syms:
        questions.append("Should a dermatological evaluation be done to determine if the rash is viral or allergic?")

    return questions[:5]
