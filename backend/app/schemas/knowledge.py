"""
HealthBridge AI - Knowledge Base Schemas
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel

class DiseaseItem(BaseModel):
    id: str
    name: str
    simple_definition: Optional[str] = None
    medical_definition: Optional[str] = None
    common_symptoms: List[str] = []
    possible_causes: List[str] = []
    risk_factors: List[str] = []
    general_prevention: List[str] = []
    common_diagnostic_tests: List[str] = []
    general_treatment: Optional[str] = None
    warning_signs: Optional[str] = None
    when_to_seek_doctor: Optional[str] = None
    faqs: List[Dict[str, str]] = []
    related_medical_terms: List[str] = []
    source: Optional[str] = None
    source_url: Optional[str] = None
    last_updated: Optional[str] = None

class MedicalTermItem(BaseModel):
    id: str
    term: str
    category: Optional[str] = None
    medical_definition: Optional[str] = None
    simple_explanation: Optional[str] = None
    very_simple_explanation: Optional[str] = None
    tamil_explanation: Optional[str] = None
    hindi_explanation: Optional[str] = None
    related_terms: List[str] = []
    source: Optional[str] = None

class LabTestItem(BaseModel):
    id: str
    name: str
    what_is_it: Optional[str] = None
    why_is_it_performed: Optional[str] = None
    what_does_it_measure: Optional[str] = None
    what_does_result_represent: Optional[str] = None
    important_limitations: Optional[str] = None
    source: Optional[str] = None
