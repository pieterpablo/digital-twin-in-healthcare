"""API-routes voor de zoekfrontend, bestaande CLI-modellen en opslag."""
from fastapi import APIRouter, HTTPException, Query
from app.models.prediction import PredictionRequest, SaveRequest
from app.services import predictions as service

router = APIRouter(tags=['Digital Twin'])


def execute(function, *args):
    try:
        return function(*args)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except OSError as error:
        raise HTTPException(status_code=500, detail='Bestand kon niet worden gelezen of opgeslagen') from error


@router.get('/patients')
@router.get('/tumor/patients')
def patients():
    return execute(service.list_patients)


@router.get('/tumor/predict/{patient_id}')
def prediction(patient_id: str, scan: int | None = Query(default=None, ge=1)):
    return execute(service.prediction, patient_id, scan)


@router.post('/predict')
def compact_prediction(request: PredictionRequest):
    return execute(service.compact_prediction, request.patient_id, request.scan_number)


@router.post('/save')
def save(request: SaveRequest):
    return execute(service.store_prediction, request.patient_id, request.scan_number, request.clear_old)
