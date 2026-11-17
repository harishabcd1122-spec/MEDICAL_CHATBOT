"""
HealthBridge AI - Automated Tests for Symptom Analysis & Safety Engines
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.safety.emergency_engine import check_emergency
from backend.app.safety.urgency_engine import evaluate_urgency
from backend.app.ml.symptom_normalizer import normalize_symptoms

client = TestClient(app)

def test_emergency_engine_detection():
    # Severe chest pain and breathing difficulty
    text = "I have severe chest pain and cannot breathe"
    res = check_emergency(text)
    assert res["is_emergency"] is True
    assert res["urgency_level"] == "URGENT"
    assert "urgent medical attention" in res["message"]

    # Tamil emergency
    res_ta = check_emergency("எனக்கு கடும் நெஞ்சு வலி இருக்கிறது")
    assert res_ta["is_emergency"] is True

    # Non-emergency
    res_mild = check_emergency("I have a runny nose and slight sneeze")
    assert res_mild["is_emergency"] is False

def test_symptom_normalizer():
    # English
    en_res = normalize_symptoms("I have high fever, terrible headache and body pain")
    assert "fever" in en_res["extracted_symptoms"]
    assert "headache" in en_res["extracted_symptoms"]
    assert "body_pain" in en_res["extracted_symptoms"]
    assert en_res["is_sufficient"] is True

    # Tamil
    ta_res = normalize_symptoms("எனக்கு காய்ச்சல் மற்றும் தலைவலி இருக்கிறது")
    assert ta_res["detected_language"] == "ta"
    assert "fever" in ta_res["extracted_symptoms"]
    assert "headache" in ta_res["extracted_symptoms"]

    # Hindi
    hi_res = normalize_symptoms("मुझे बुखार और सिरदर्द है")
    assert hi_res["detected_language"] == "hi"
    assert "fever" in hi_res["extracted_symptoms"]
    assert "headache" in hi_res["extracted_symptoms"]

def test_symptom_api_emergency_override():
    payload = {"symptoms": "Sudden severe chest pressure and shortness of breath"}
    res = client.post("/symptoms/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_emergency"] is True
    assert data["urgency"]["urgency_level"] == "URGENT"
    assert "urgent medical attention" in data["explanation"].lower()
    # ML model matching must NOT execute when acute emergency is detected
    assert len(data["possible_conditions"]) == 0

def test_symptom_api_valid_matching():
    payload = {"symptoms": "I have fever, headache, body pain and chills"}
    res = client.post("/symptoms/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["is_emergency"] is False
    assert len(data["possible_conditions"]) > 0

    top = data["possible_conditions"][0]
    assert "condition" in top
    assert "model_match_score" in top
    assert "score_display" in top
    # Check disclaimer note
    assert "NOT the probability" in data["score_note"]
    assert len(data["questions_for_doctor"]) > 0

def test_symptom_api_insufficient_information():
    payload = {"symptoms": "hello there"}
    res = client.post("/symptoms/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "insufficient_information"
    assert "don't have enough reliable information" in data["explanation"]
