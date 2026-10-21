from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import sys

router = APIRouter(prefix="/tumor", tags=["Digital Twin"])

MODEL_DIR = Path(__file__).resolve().parents[2] / "Algoritme_met_model"
sys.path.insert(0, str(MODEL_DIR))

from run_voorspelling import predict_patient

DATA_FILE = MODEL_DIR / "fake_patients.json"


@router.get("/patients")
def get_patients():
    with DATA_FILE.open(encoding="utf-8") as f:
        data = json.load(f)

    if data.get("synthetic") is not True:
        raise HTTPException(400, "Only synthetic test data allowed")

    return [
        {"id": p["id"], "name": p["name"]}
        for p in data["patients"]
    ]


@router.get("/predict/{patient_id}")
def get_prediction(patient_id: str):
    try:
        result = predict_patient(
            patient_id,
            data_file=DATA_FILE,
            n_samples=2000
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return {
        "simulation_only": True,
        "patient_id": result["patient_id"],
        "name": result["name"],
        "variables": result["variables"],
        "forecast_history": result["forecast_history"],
        "latest_forecast": result["latest_forecast"]
    }
    
