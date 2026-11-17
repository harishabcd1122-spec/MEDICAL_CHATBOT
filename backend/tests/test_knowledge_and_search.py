"""
HealthBridge AI - Automated Tests for Knowledge Base & Search
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_list_and_get_diseases():
    res = client.get("/diseases")
    assert res.status_code == 200
    diseases = res.json()
    assert len(diseases) >= 20

    # Specific disease
    d_res = client.get("/diseases/dengue")
    assert d_res.status_code == 200
    data = d_res.json()
    assert data["name"] == "Dengue"
    assert "Platelets" in data["related_medical_terms"]
    assert len(data["common_symptoms"]) > 0

def test_disease_not_found():
    res = client.get("/diseases/unsupported-illness-xyz")
    assert res.status_code == 404
    assert "outside the current prototype's supported disease set" in res.json()["detail"]

def test_list_and_get_medical_terms():
    res = client.get("/medical-terms")
    assert res.status_code == 200
    terms = res.json()
    assert len(terms) >= 30

    # Check multilingual translations for HbA1c
    h_res = client.get("/medical-terms/hba1c")
    assert h_res.status_code == 200
    data = h_res.json()
    assert "சராசரி சர்க்கரை" in data["tamil_explanation"]
    assert "औसत रक्त शर्करा" in data["hindi_explanation"]

def test_global_search():
    res = client.get("/search?q=platelet")
    assert res.status_code == 200
    data = res.json()
    assert data["total_results"] > 0
    # Should find platelet term and dengue disease
    term_names = [t["term"] for t in data["results"]["medical_terms"]]
    assert "Platelets" in term_names

def test_ml_evaluation_endpoint():
    res = client.get("/ml/evaluation")
    assert res.status_code == 200
    data = res.json()
    assert "Prototype ML Evaluation" in data["title"]
    assert "clinical diagnostic accuracy" in data["notice"]
    assert "Random Forest (Baseline)" in data["data"]["comparison"]
