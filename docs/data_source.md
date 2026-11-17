# HealthBridge AI — Dataset Provenance & Methodology

## 1. Dataset Overview
- **Dataset Name**: HealthBridge 20-Condition Disease-Symptom Demo Dataset (HB-DS-20)
- **Dataset Type**: Synthetic/demo data; it contains no sourced patient records.
- **Generation Source**: `ml/preprocessing/prepare_dataset.py` defines hand-authored symptom probability profiles and samples binary features with NumPy. Unlisted symptoms receive a 0.02 baseline probability, and rows with fewer than two active profile symptoms are adjusted to activate the two highest-probability profile symptoms.
- **External Source and License**: No external dataset was used to produce this CSV. The prior references to Columbia/NewYork-Presbyterian, Kaggle/UCI, PDDL, and CC-BY were not substantiated by source files and are withdrawn; no external license is claimed for the generated data.
- **Version**: 1.0.0
- **Scope**: Educational software demonstration only. The profiles are assumptions encoded by this project, not clinically validated prevalence estimates.

## 2. Dataset Characteristics
- **Total Records**: 1,200 generated feature rows across 20 disease labels.
- **Distribution**: 60 generated rows per label. They are not observed typical or atypical patient presentations.
- **Number of Symptom Features**: 42 standardized binary symptom indicators.
- **Disease Labels (Target Variable)**:
  1. Common cold
  2. Influenza
  3. Dengue
  4. Malaria
  5. Typhoid
  6. COVID-19
  7. Migraine
  8. Asthma
  9. Pneumonia
  10. Diabetes
  11. Hypertension
  12. Gastritis
  13. GERD
  14. Urinary tract infection (UTI)
  15. Tuberculosis
  16. Anemia
  17. Sinusitis
  18. Food poisoning
  19. Viral fever
  20. Chickenpox

## 3. Standardized Symptom Feature Set
1. `fever`
2. `chills`
3. `high_fever`
4. `mild_fever`
5. `headache`
6. `severe_headache`
7. `throbbing_headache`
8. `cough`
9. `dry_cough`
10. `productive_cough`
11. `cough_with_blood`
12. `fatigue`
13. `malaise`
14. `body_pain`
15. `muscle_pain`
16. `joint_pain`
17. `chest_pain`
18. `shortness_of_breath`
19. `wheezing`
20. `nausea`
21. `vomiting`
22. `diarrhea`
23. `abdominal_pain`
24. `stomach_burning`
25. `acid_reflux`
26. `heartburn`
27. `loss_of_appetite`
28. `unexplained_weight_loss`
29. `skin_rash`
30. `itching`
31. `red_spots_blisters`
32. `pale_skin`
33. `dizziness`
34. `excessive_thirst`
35. `frequent_urination`
36. `burning_urination`
37. `pelvic_discomfort`
38. `runny_nose`
39. `nasal_congestion`
40. `facial_pressure_sinus`
41. `loss_of_smell_taste`
42. `night_sweats`

## 4. Training, Evaluation, and Leakage
- **Splits**: `StratifiedGroupKFold` partitions data by identical 42-feature vectors. A five-fold split reserves test data; a four-fold split of the remainder separates training and validation. Current sizes are 719/241/240 rows (training/validation/test); group sizes make exact nominal percentages inexact.
- **Model Selection**: Candidate models are fitted on training rows and selected by macro F1 on validation rows. The selected model is refitted on train plus validation rows. The test rows are evaluated only after selection and refitting; they do not determine the selected model.
- **Preprocessing**: The CSV's synthetic feature generation and fixed feature names are defined before model splitting; training applies no data-fitted normalization or imputation. Natural-language symptom normalization is a separate fixed keyword/synonym mapping at inference time.
- **Limit of the Holdout**: The random held-out test rows are from the same synthetic generator and hand-authored profiles as training rows. Similar generated feature patterns can occur across splits, so these metrics do not establish generalization to real patients or clinical use.

## 5. Known Limitations & Prototype Boundaries
1. **Not a Clinical Diagnostic Tool**: This synthetic dataset is not evidence of real symptom-disease relationships. It does not account for patient histories, examination findings, diagnostic tests, or real-world prevalence.
2. **Limited Condition Scope**: The model is bounded strictly to the 20 supported conditions. Manifestations of conditions outside these 20 will be flagged as out-of-scope or mapped to closest prototype matches.
3. **No Clinical Severity Weighting**: Disease progression and complex comorbidities are not modeled.
4. **Emergency Priority**: Severe indicators (such as crushing chest pain or acute respiratory arrest) bypass ML scoring entirely and are escalated to immediate emergency triage.
