"""
HealthBridge AI - Synthetic Demo Dataset Generation
Generates synthetic symptom-feature rows from hand-authored condition profiles.
This is not an external patient dataset or clinically validated benchmark.
"""

import os
import numpy as np
import pandas as pd

# Define the 42 standardized symptoms
SYMPTOMS = [
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

# Hand-authored synthetic demo probabilities; these are not clinically validated estimates.
DISEASE_PROFILES = {
    "Common cold": {
        "runny_nose": 0.95, "nasal_congestion": 0.90, "cough": 0.80, "mild_fever": 0.50,
        "headache": 0.60, "fatigue": 0.65, "malaise": 0.55
    },
    "Influenza": {
        "fever": 0.95, "high_fever": 0.85, "chills": 0.85, "headache": 0.85,
        "fatigue": 0.95, "body_pain": 0.90, "muscle_pain": 0.90, "cough": 0.80,
        "dry_cough": 0.70, "malaise": 0.85
    },
    "Dengue": {
        "fever": 0.98, "high_fever": 0.90, "severe_headache": 0.85, "joint_pain": 0.90,
        "muscle_pain": 0.90, "body_pain": 0.85, "nausea": 0.75, "vomiting": 0.70,
        "skin_rash": 0.80, "fatigue": 0.85, "loss_of_appetite": 0.70
    },
    "Malaria": {
        "fever": 0.98, "high_fever": 0.92, "chills": 0.95, "headache": 0.85,
        "nausea": 0.70, "vomiting": 0.65, "body_pain": 0.80, "fatigue": 0.90
    },
    "Typhoid": {
        "fever": 0.95, "high_fever": 0.85, "headache": 0.80, "abdominal_pain": 0.85,
        "loss_of_appetite": 0.80, "diarrhea": 0.55, "fatigue": 0.85, "malaise": 0.75
    },
    "COVID-19": {
        "fever": 0.85, "dry_cough": 0.85, "cough": 0.90, "loss_of_smell_taste": 0.80,
        "fatigue": 0.85, "shortness_of_breath": 0.55, "body_pain": 0.70, "headache": 0.65
    },
    "Migraine": {
        "headache": 0.98, "throbbing_headache": 0.95, "severe_headache": 0.90,
        "nausea": 0.80, "vomiting": 0.60, "dizziness": 0.70
    },
    "Asthma": {
        "shortness_of_breath": 0.95, "wheezing": 0.95, "cough": 0.80, "dry_cough": 0.65,
        "chest_pain": 0.50
    },
    "Pneumonia": {
        "fever": 0.90, "high_fever": 0.80, "chills": 0.75, "cough": 0.95,
        "productive_cough": 0.85, "chest_pain": 0.80, "shortness_of_breath": 0.85,
        "fatigue": 0.80
    },
    "Diabetes": {
        "excessive_thirst": 0.95, "frequent_urination": 0.95, "fatigue": 0.85,
        "unexplained_weight_loss": 0.75, "dizziness": 0.50
    },
    "Hypertension": {
        "headache": 0.70, "dizziness": 0.75, "fatigue": 0.50, "chest_pain": 0.40
    },
    "Gastritis": {
        "abdominal_pain": 0.90, "stomach_burning": 0.95, "nausea": 0.75, "vomiting": 0.60,
        "loss_of_appetite": 0.70, "acid_reflux": 0.65
    },
    "GERD": {
        "acid_reflux": 0.98, "heartburn": 0.95, "stomach_burning": 0.80, "chest_pain": 0.60,
        "nausea": 0.50
    },
    "UTI": {
        "burning_urination": 0.98, "frequent_urination": 0.90, "pelvic_discomfort": 0.85,
        "mild_fever": 0.50, "fever": 0.45
    },
    "Tuberculosis": {
        "cough": 0.95, "cough_with_blood": 0.75, "productive_cough": 0.85,
        "mild_fever": 0.80, "night_sweats": 0.90, "unexplained_weight_loss": 0.90,
        "fatigue": 0.85, "chest_pain": 0.65
    },
    "Anemia": {
        "fatigue": 0.98, "pale_skin": 0.90, "dizziness": 0.85, "shortness_of_breath": 0.65,
        "malaise": 0.80
    },
    "Sinusitis": {
        "facial_pressure_sinus": 0.95, "nasal_congestion": 0.90, "headache": 0.85,
        "runny_nose": 0.75, "cough": 0.50, "mild_fever": 0.40
    },
    "Food poisoning": {
        "nausea": 0.95, "vomiting": 0.95, "diarrhea": 0.90, "abdominal_pain": 0.90,
        "fever": 0.50, "fatigue": 0.70, "chills": 0.50
    },
    "Viral fever": {
        "fever": 0.98, "mild_fever": 0.70, "headache": 0.80, "body_pain": 0.85,
        "fatigue": 0.85, "joint_pain": 0.60, "malaise": 0.75
    },
    "Chickenpox": {
        "skin_rash": 0.98, "itching": 0.95, "red_spots_blisters": 0.95, "fever": 0.85,
        "fatigue": 0.80, "loss_of_appetite": 0.75
    }
}

def generate_dataset(samples_per_disease=60, random_seed=42):
    np.random.seed(random_seed)
    records = []

    for disease, profile in DISEASE_PROFILES.items():
        for _ in range(samples_per_disease):
            record = {"disease": disease}
            for sym in SYMPTOMS:
                base_prob = profile.get(sym, 0.02)  # Low baseline noise for non-characteristic symptoms
                record[sym] = 1 if np.random.rand() < base_prob else 0

            # Ensure at least 2 characteristic symptoms are active for the condition
            active_chars = [s for s, p in profile.items() if record[s] == 1]
            if len(active_chars) < 2:
                top_syms = sorted(profile.keys(), key=lambda k: profile[k], reverse=True)[:2]
                for s in top_syms:
                    record[s] = 1

            records.append(record)

    df = pd.DataFrame(records)
    return df

if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    df = generate_dataset(samples_per_disease=60, random_seed=42)
    output_path = os.path.join(output_dir, "disease_symptoms_dataset.csv")
    df.to_csv(output_path, index=False)
    print(f"Generated dataset with {len(df)} samples across {df['disease'].nunique()} conditions.")
    print(f"Saved to: {output_path}")
