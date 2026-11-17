"""
HealthBridge AI - Symptom Normalization Engine
Normalizes multilingual natural language input (English, Tamil, Hindi)
into standardized feature vectors mapped to the 42 dataset features.
Handles common spelling variations, synonyms, and phrase variations.
"""

from typing import Dict, Any, List, Set, Tuple
import re

FEATURE_SYMPTOMS = [
    "fever", "chills", "high_fever", "mild_fever", "headache", "severe_headache",
    "throbbing_headache", "cough", "dry_cough", "productive_cough", "cough_with_blood",
    "fatigue", "malaise", "body_pain", "muscle_pain", "joint_pain", "chest_pain",
    "shortness_of_breath", "wheezing", "nausea", "vomiting", "diarrhea",
    "abdominal_pain", "stomach_burning", "acid_reflux", "heartburn", "loss_of_appetite",
    "unexplained_weight_loss", "skin_rash", "itching", "red_spots_blisters",
    "pale_skin", "dizziness", "excessive_thirst", "frequent_urination",
    "burning_urination", "pelvic_discomfort", "runny_nose", "nasal_congestion",
    "facial_pressure_sinus", "loss_of_smell_taste", "night_sweats"
]

# Multilingual and synonym keyword mappings
SYMPTOM_MAPPINGS: List[Tuple[str, List[str]]] = [
    # Severe / Red flag variants
    ("cough_with_blood", ["cough with blood", "coughing blood", "blood in cough", "hemoptysis", "இரத்த இருமல்", "खांसी में खून"]),
    ("shortness_of_breath", ["shortness of breath", "difficulty breathing", "breathless", "breathlessness", "cannot breathe", "dyspnea", "மூச்சுத்திணறல்", "மூச்சு திணறல்", "सांस फूलना", "सांस लेने में दिक्कत"]),
    ("chest_pain", ["chest pain", "tightness in chest", "chest tightness", "chest pressure", "pain in chest", "நெஞ்சு வலி", "நெஞ்சில் வலி", "सीने में दर्द"]),
    ("throbbing_headache", ["throbbing headache", "one sided headache", "migraine headache", "ஒற்றைத் தலைவலி", "आधा सिर दर्द"]),
    ("severe_headache", ["severe headache", "terrible headache", "bad headache", "தீவிர தலைவலி", "तेज सिरदर्द"]),
    ("headache", ["headache", "head ache", "head hurts", "pain in head", "headaches", "தலைவலி", "தலை வலி", "सिरदर्द", "सिर दर्द"]),
    ("high_fever", ["high fever", "very high fever", "burning up", "அதிக காய்ச்சல்", "तेज बुखार"]),
    ("mild_fever", ["mild fever", "low grade fever", "slight fever", "இலேசான காய்ச்சல்", "हल्का बुखार"]),
    ("fever", ["fever", "fevers", "feverish", "temperature", "pyrexia", "bukhar", "காய்ச்சல்", "சுரம்", "बुखार"]),
    ("chills", ["chills", "shivering", "feeling cold", "rigors", "குளிர்", "நடுக்கம்", "कंपकंपी", "ठंड लगना"]),
    ("dry_cough", ["dry cough", "dry coughing", "வறட்டு இருமல்", "सूखी खांसी"]),
    ("productive_cough", ["productive cough", "wet cough", "cough with phlegm", "cough with mucus", "சளி இருமல்", "कफ वाली खांसी", "बलगम वाली खांसी"]),
    ("cough", ["cough", "coughing", "khansi", "இருமல்", "இருமால்", "खांसी"]),
    ("loss_of_smell_taste", ["loss of smell", "loss of taste", "cannot smell", "cannot taste", "anosmia", "ageusia", "வாசனை இழப்பு", "சுவை இழப்பு", "सूंघने की क्षमता खोना", "स्वाद न आना"]),
    ("facial_pressure_sinus", ["sinus", "facial pressure", "sinusitis", "pain in forehead", "முக அழுத்தம்", "சைனஸ்", "साइनस का दर्द"]),
    ("nasal_congestion", ["nasal congestion", "stuffy nose", "blocked nose", "nose blocked", "மூக்கடைப்பு", "மூக்கு அடைப்பு", "बंद नाक"]),
    ("runny_nose", ["runny nose", "running nose", "cold", "sneezing", "மூக்கு ஒழுகுதல்", "बहती नाक"]),
    ("burning_urination", ["burning urination", "painful urination", "burning while peeing", "dysuria", "சிறுநீர் எரிச்சல்", "பச்சை சிறுநீர்", "पेशाब में जलन"]),
    ("frequent_urination", ["frequent urination", "peeing often", "urinating frequently", "அடிக்கடி சிறுநீர்", "बार-बार पेशाब आना"]),
    ("pelvic_discomfort", ["pelvic pain", "pelvic discomfort", "lower abdominal pain", "அடிவயிற்று வலி", "पेल्विक दर्द"]),
    ("stomach_burning", ["stomach burning", "burning sensation in stomach", "வயிற்று எரிச்சல்", "पेट में जलन"]),
    ("heartburn", ["heartburn", "burning in chest after eating", "நெஞ்செரிச்சல்", "सीने में जलन"]),
    ("acid_reflux", ["acid reflux", "acidity", "sour burps", "அமிலத்தன்மை", "एसिडिटी", "खट्टी डकार"]),
    ("abdominal_pain", ["abdominal pain", "stomach ache", "stomach pain", "tummy ache", "belly pain", "வயிற்று வலி", "पेट दर्द"]),
    ("diarrhea", ["diarrhea", "loose motions", "loose stool", "watery stool", "dysentery", "வயிற்றுப்போக்கு", "பேதி", "दस्त"]),
    ("vomiting", ["vomiting", "throwing up", "puking", "vomited", "வாந்தி", "உல்டி", "उल्टी"]),
    ("nausea", ["nausea", "feeling nauseous", "feeling like vomiting", "queasy", "குமட்டல்", "जी मिचलाना"]),
    ("fatigue", ["fatigue", "tired", "exhaustion", "weakness", "lethargy", "சோர்வு", "களைப்பு", "थकान", "कमजोरी"]),
    ("malaise", ["malaise", "feeling unwell", "sick feeling", "உடல் நலம் சரியில்லை", "अस्वस्थ महसूस होना"]),
    ("muscle_pain", ["muscle pain", "muscle ache", "myalgia", "தசை வலி", "मांसपेशियों में दर्द"]),
    ("joint_pain", ["joint pain", "arthralgia", "knee pain", "joints ache", "மூட்டு வலி", "जोड़ों का दर्द"]),
    ("body_pain", ["body pain", "body ache", "whole body hurts", "bodyache", "உடல் வலி", "உடம்பு வலி", "बदन दर्द", "शरीर में दर्द"]),
    ("wheezing", ["wheezing", "whistling sound while breathing", "விசிலிங் சத்தம்", "घरघराहट"]),
    ("skin_rash", ["skin rash", "rashes", "spots on skin", "தடிப்பு", "தோல் தடிப்பு", "त्वचा पर चकत्ते"]),
    ("red_spots_blisters", ["red spots", "blisters", "fluid filled spots", "கொப்புளங்கள்", "फफोले", "लाल दाने"]),
    ("itching", ["itching", "itchy", "scratching", "அரிப்பு", "खुजली"]),
    ("pale_skin", ["pale skin", "paleness", "வெளிறிய தோல்", "पीलापन"]),
    ("dizziness", ["dizziness", "dizzy", "lightheaded", "head spinning", "தலைசுற்றல்", "चक्कर आना"]),
    ("excessive_thirst", ["excessive thirst", "very thirsty", "polydipsia", "அதிக தாகம்", "अत्यधिक प्यास"]),
    ("unexplained_weight_loss", ["unexplained weight loss", "sudden weight loss", "losing weight", "எடை இழப்பு", "वजन कम होना"]),
    ("loss_of_appetite", ["loss of appetite", "not feeling hungry", "anorexia", "பசியின்மை", "भूख न लगना"]),
    ("night_sweats", ["night sweats", "sweating at night", "இரவு வியர்வை", "रात में पसीना आना"])
]

def detect_language(text: str) -> str:
    """Detects primary language family based on unicode scripts."""
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "ta"
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    return "en"

def normalize_symptoms(user_text: str) -> Dict[str, Any]:
    """
    Parses user natural language, identifies symptoms, normalizes synonyms,
    and constructs the standardized feature vector.
    """
    text = (user_text or "").lower()
    lang = detect_language(user_text)

    # Basic punctuation cleanup
    cleaned = re.sub(r"[^\w\s\u0B80-\u0BFF\u0900-\u097F]", " ", text)
    cleaned = " ".join(cleaned.split())

    identified_symptoms: Set[str] = set()

    for sym_name, patterns in SYMPTOM_MAPPINGS:
        for pat in patterns:
            # Check for exact phrase or word boundary match
            regex = r"(?:^|\s)" + re.escape(pat.lower()) + r"(?:$|\s)"
            if re.search(regex, cleaned):
                identified_symptoms.add(sym_name)
                # If specific variant found, automatically imply parent if appropriate
                if sym_name in ("high_fever", "mild_fever"):
                    identified_symptoms.add("fever")
                elif sym_name in ("severe_headache", "throbbing_headache"):
                    identified_symptoms.add("headache")
                elif sym_name in ("dry_cough", "productive_cough", "cough_with_blood"):
                    identified_symptoms.add("cough")
                break

    # Build 42-feature binary vector
    features_dict = {sym: (1 if sym in identified_symptoms else 0) for sym in FEATURE_SYMPTOMS}
    symptom_list = sorted(list(identified_symptoms))

    return {
        "raw_text": user_text,
        "detected_language": lang,
        "extracted_symptoms": symptom_list,
        "symptom_count": len(symptom_list),
        "feature_vector": features_dict,
        "is_sufficient": len(symptom_list) >= 1
    }
