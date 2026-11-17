"""
HealthBridge AI - Symptom Analysis Schemas
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SymptomAnalyzeRequest(BaseModel):
    symptoms: str = Field(..., min_length=2, max_length=2000, description="Natural language symptoms text")
    language: Optional[str] = Field("en", description="Optional language preference (en, ta, hi)")

class ConditionMatch(BaseModel):
    condition: str
    raw_score: float
    model_match_score: float
    score_display: str

class UrgencyDetails(BaseModel):
    urgency_level: str
    badge_color: str
    level_note: str
    explanation: str
    urgent_symptoms_flagged: List[str] = []
    questions_for_doctor: List[str] = []

class SymptomAnalyzeResponse(BaseModel):
    status: str
    raw_input: str
    detected_language: str
    is_emergency: bool = False
    emergency_details: Optional[Dict[str, Any]] = None
    extracted_symptoms: List[str] = []
    possible_conditions: List[ConditionMatch] = []
    urgency: Optional[UrgencyDetails] = None
    explanation: str
    score_note: Optional[str] = None
    questions_for_doctor: List[str] = []
    disclaimer: str
