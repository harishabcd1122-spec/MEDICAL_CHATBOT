"""
HealthBridge AI - Global Medical Disclaimer and Standard Safety Text
"""

GLOBAL_DISCLAIMER_EN = (
    "This chatbot provides general health information and educational assistance. "
    "It does not provide a medical diagnosis and does not replace a qualified doctor or healthcare professional. "
    "Information may be incomplete or inaccurate and should not be used as a substitute for professional "
    "medical advice, diagnosis or treatment. Seek immediate medical attention for severe or emergency symptoms."
)

GLOBAL_DISCLAIMER_TA = (
    "இந்த சாட்பாட் பொதுவான சுகாதார தகவல்களையும் கல்வி உதவிகளையும் வழங்குகிறது. "
    "இது மருத்துவ நோயறிதலை வழங்காது மற்றும் தகுதியான மருத்துவருக்கு மாற்றாகாது. "
    "தீவிரமான அல்லது அவசர அறிகுறிகளுக்கு உடனடியாக மருத்துவ உதவியை நாடுங்கள்."
)

GLOBAL_DISCLAIMER_HI = (
    "यह चैटबॉट केवल सामान्य स्वास्थ्य जानकारी और शैक्षिक सहायता प्रदान करता है। "
    "यह कोई चिकित्सीय निदान (Diagnosis) नहीं देता है और किसी योग्य डॉक्टर का विकल्प नहीं है। "
    "गंभीर या आपातकालीन लक्षणों के लिए तत्काल पेशेवर चिकित्सा सहायता लें।"
)

MODEL_SCORE_NOTE = (
    "Important: This score reflects the prototype model's classification on its supported dataset. "
    "It is NOT the probability that you have this disease and must not be interpreted as a medical diagnosis."
)

URGENCY_LEVEL_NOTE = (
    "Urgency/Safety Level refers to safety and triage indicators. "
    "It does not represent the probability of having a disease."
)

def get_disclaimer(language: str = "en") -> str:
    lang = (language or "en").lower()
    if "ta" in lang or "tamil" in lang:
        return GLOBAL_DISCLAIMER_TA
    if "hi" in lang or "hindi" in lang:
        return GLOBAL_DISCLAIMER_HI
    return GLOBAL_DISCLAIMER_EN
