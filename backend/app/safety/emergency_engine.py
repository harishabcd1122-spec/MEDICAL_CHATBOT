"""
HealthBridge AI - Rule-Based Emergency Safety Engine
Executes pre-inference screening for life-threatening presentations.
Emergency guidance overrides normal chatbot and ML pipelines.
"""

from typing import Dict, Any, List
import re

EMERGENCY_TRIGGERS = [
    # Chest pain & Cardiac
    {
        "id": "severe_chest_pain",
        "patterns": [
            r"\b(severe|crushing|heavy|unbearable)\s+(chest\s+pain|chest\s+pressure|heart\s+pain)\b",
            r"\b(chest\s+pain)\s+with\s+(sweating|shortness of breath|radiating|left arm|jaw)\b",
            r"\bheart\s+attack\b",
            r"நெஞ்சு\s*வலி", r"கடும்\s*நெஞ்சு\s*வலி",
            r"सीने\s*में\s*तेज़\s*दर्द", r"दिल\s*का\s*दौरा"
        ],
        "category": "Cardiac / Severe Chest Pain"
    },
    # Severe Dyspnea / Respiratory
    {
        "id": "severe_breathing_difficulty",
        "patterns": [
            r"\b(cannot|unable to|can't)\s+breathe\b",
            r"\b(severe|gasping for|struggling to|extreme)\s+(difficulty breathing|breathlessness|shortness of breath)\b",
            r"\bchoking\b", r"\bcyanosis|blue\s+lips\b",
            r"மூச்சு\s*திணறல்", r"மூச்சுவிட\s*முடியவில்லை",
            r"सांस\s*नहीं\s*ले\s*पा\s*रहा", r"गंभीर\s*सांस\s*की\s*तकलीफ"
        ],
        "category": "Acute Respiratory Distress"
    },
    # Loss of consciousness / Syncope
    {
        "id": "loss_of_consciousness",
        "patterns": [
            r"\b(loss of consciousness|passed out|blacked out|unresponsive|unconscious|fainted suddenly)\b",
            r"மயக்கம்", r"நினைவிழந்த",
            r"बेहोश", r"होश\s*खो\s*बैठ"
        ],
        "category": "Loss of Consciousness"
    },
    # Seizures / Convulsions
    {
        "id": "seizures",
        "patterns": [
            r"\b(seizure|seizures|convulsions|epileptic fit|active fitting)\b",
            r"வலிப்பு", r"காக்காய்\s*வலிப்பு",
            r"दौरा", r"मिर्गी\s*का\s*दौरा"
        ],
        "category": "Seizures / Neurological Convulsion"
    },
    # Severe Bleeding / Hemorrhage
    {
        "id": "severe_bleeding",
        "patterns": [
            r"\b(severe bleeding|uncontrolled bleeding|gushing blood|coughing blood|vomiting blood|hematemesis)\b",
            r"அதிக\s*இரத்தப்போக்கு", r"இரத்தம்\s*கக்கு",
            r"अत्यधिक\s*रक्तस्राव", r"खून\s*की\s*उल्टी"
        ],
        "category": "Severe Hemorrhage"
    },
    # Anaphylaxis / Allergic Reaction
    {
        "id": "anaphylaxis",
        "patterns": [
            r"\b(anaphylaxis|throat swelling|swollen tongue|throat closing up|allergic reaction difficulty breathing)\b",
            r"தொண்டை\s*வீக்கம்",
            r"गले\s*में\s*सूजन", r"गंभीर\s*एलर्जी"
        ],
        "category": "Suspected Anaphylaxis"
    },
    # Stroke / Sudden Neurological Deficit
    {
        "id": "stroke_symptoms",
        "patterns": [
            r"\b(sudden facial drooping|face drooping|sudden arm weakness|sudden slurred speech|sudden paralysis|stroke signs)\b",
            r"முக\s*வாதம்", r"பேச்சு\s*குளறு",
            r"चेहरा\s*टेढ़ा", r"अचानक\s*कमजोरी", r"फालिज"
        ],
        "category": "Suspected Acute Stroke"
    }
]

def check_emergency(user_text: str) -> Dict[str, Any]:
    """
    Scans input for high-urgency/red-flag indicators.
    Returns structured emergency advisory if detected.
    """
    text = (user_text or "").lower()
    matched_triggers = []

    for trigger in EMERGENCY_TRIGGERS:
        for pattern in trigger["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                matched_triggers.append(trigger["category"])
                break

    if matched_triggers:
        return {
            "is_emergency": True,
            "matched_categories": list(set(matched_triggers)),
            "urgency_level": "URGENT",
            "message": (
                "These symptoms may require urgent medical attention. "
                "Please seek immediate professional medical care or emergency assistance."
            ),
            "tamil_message": (
                "இந்த அறிகுறிகளுக்கு உடனடி அவசர மருத்துவ சிகிச்சை தேவைப்படலாம். "
                "தயவுசெய்து உடனடியாக அவசர மருத்துவ சேவையை அல்லது மருத்துவரை அணுகவும்."
            ),
            "hindi_message": (
                "इन लक्षणों के लिए तत्काल आपातकालीन चिकित्सा सहायता की आवश्यकता हो सकती है। "
                "कृपया तुरंत नजदीकी आपातकालीन चिकित्सा सेवा या अस्पताल से संपर्क करें।"
            ),
            "action_guidelines": [
                "Call local emergency services immediately (e.g., 112 / 108 / 911).",
                "Do not wait or rely on an online application for acute symptoms.",
                "Have someone remain with the person if consciousness is impaired.",
                "If experiencing chest pressure, sit down and remain calm while help arrives."
            ]
        }

    return {
        "is_emergency": False,
        "matched_categories": [],
        "urgency_level": "LOW",
        "message": ""
    }
