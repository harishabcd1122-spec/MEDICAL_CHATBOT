"""
HealthBridge AI - Model Training & Evaluation Pipeline
Trains and compares Random Forest, Logistic Regression, and Decision Tree
using validation-based selection and grouped stratified holdouts.
"""

import json
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

def calculate_metrics(y_true, y_pred, disease_classes):
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision_macro": round(float(precision_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "recall_macro": round(float(recall_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "f1_macro": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=disease_classes).tolist()
    }

def train_and_evaluate():
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "disease_symptoms_dataset.csv")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}")

    df = pd.read_csv(data_path)
    X = df.drop(columns=["disease"])
    y = df["disease"]
    symptom_features = list(X.columns)
    disease_classes = sorted(y.unique().tolist())

    # Keep identical feature vectors together so duplicates cannot cross splits.
    feature_groups = X.apply(lambda row: tuple(row), axis=1)
    test_splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    train_validation_indices, test_indices = next(
        test_splitter.split(X, y, groups=feature_groups)
    )
    X_train_validation = X.iloc[train_validation_indices]
    X_test = X.iloc[test_indices]
    y_train_validation = y.iloc[train_validation_indices]
    y_test = y.iloc[test_indices]

    validation_splitter = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=24)
    train_indices, validation_indices = next(
        validation_splitter.split(
            X_train_validation,
            y_train_validation,
            groups=feature_groups.iloc[train_validation_indices]
        )
    )
    X_train = X_train_validation.iloc[train_indices]
    X_validation = X_train_validation.iloc[validation_indices]
    y_train = y_train_validation.iloc[train_indices]
    y_validation = y_train_validation.iloc[validation_indices]

    models = {
        "Random Forest (Baseline)": RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42),
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Decision Tree": DecisionTreeClassifier(max_depth=14, random_state=42)
    }

    validation_comparison = {}
    best_model_name = "Random Forest (Baseline)"
    best_f1 = -1
    best_model_obj = None

    for name, clf in models.items():
        # Fit strictly on train data to prevent data leakage
        clf.fit(X_train, y_train)
        validation_metrics = calculate_metrics(
            y_validation, clf.predict(X_validation), disease_classes
        )
        validation_comparison[name] = validation_metrics

        print(f"[{name}] Validation macro F1: {validation_metrics['f1_macro']:.4f}")

        if validation_metrics["f1_macro"] > best_f1:
            best_f1 = validation_metrics["f1_macro"]
            best_model_name = name
            best_model_obj = clf

    best_model_obj.fit(X_train_validation, y_train_validation)
    best_model_metrics = calculate_metrics(
        y_test, best_model_obj.predict(X_test), disease_classes
    )
    print(f"[{best_model_name}] Untouched test metrics: {best_model_metrics}")

    # Save model artifacts
    models_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    eval_dir = os.path.join(os.path.dirname(__file__), "..", "evaluation")
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(eval_dir, exist_ok=True)

    # Save best model bundle
    bundle = {
        "model_name": best_model_name,
        "model": best_model_obj,
        "features": symptom_features,
        "classes": disease_classes,
        "version": "1.0.0"
    }
    joblib.dump(bundle, os.path.join(models_dir, "best_model.joblib"))

    # Save evaluation summary
    eval_summary = {
        "dataset_name": "HealthBridge 20-Condition Disease-Symptom Benchmark (HB-DS-20)",
        "dataset_version": "1.0.0",
        "dataset_type": "synthetic_demo",
        "dataset_provenance": (
            "Generated locally by ml/preprocessing/prepare_dataset.py from hand-authored "
            "symptom probability profiles; not an external patient or clinical dataset."
        ),
        "total_samples": len(df),
        "train_samples": len(X_train_validation),
        "model_selection_train_samples": len(X_train),
        "validation_samples": len(X_validation),
        "test_samples": len(X_test),
        "number_of_diseases": len(disease_classes),
        "number_of_symptoms": len(symptom_features),
        "best_model": best_model_name,
        "best_model_metrics": best_model_metrics,
        "comparison_split": "validation",
        "comparison": validation_comparison,
        "evaluation_split": "untouched stratified test set",
        "classes": disease_classes,
        "disclaimer": "Model performance on a dataset does not represent clinical diagnostic accuracy."
    }

    with open(os.path.join(eval_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)

    print(f"\nTraining complete. Best model '{best_model_name}' saved to {models_dir}/best_model.joblib")
    print(f"Metrics saved to {eval_dir}/metrics.json")

if __name__ == "__main__":
    train_and_evaluate()
