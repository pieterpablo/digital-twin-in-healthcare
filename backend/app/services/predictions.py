"""Koppeling met de ongewijzigd overgenomen modelcode."""
import json
from pathlib import Path
import sys
from threading import Lock

MODEL_DIR = Path(__file__).resolve().parents[2] / 'Algoritme_met_model'
sys.path.insert(0, str(MODEL_DIR))

from adaptive_curve import build_full_treatment_trajectory
from run_voorspelling import compact_patient, patient_output_path, predict_patient, save_predictions

DATA_FILE = MODEL_DIR / 'fake_patients.json'
OUTPUT_DIR = MODEL_DIR / 'voorspellingen_output'
SAVE_LOCK = Lock()


def list_patients():
    data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
    if data.get('synthetic') is not True:
        raise ValueError('Alleen fictieve gegevens toegestaan')
    return [{'id': p['id'], 'name': p['name'], 'scans': [
        {'scan_number': i, 'day': scan['day']} for i, scan in enumerate(p['ct_scans'], 1)]}
        for p in data['patients']]


def prediction(patient_id, scan_number=None):
    patient = predict_patient(patient_id, data_file=DATA_FILE, scan_number=scan_number)
    reports = patient['forecast_history'] + [patient['latest_forecast']]
    patient['latest_forecast']['full_treatment_trajectory'] = build_full_treatment_trajectory(reports)
    patient['available_scans'] = next(p['scans'] for p in list_patients() if p['id'] == patient['patient_id'])
    return patient


def compact_prediction(patient_id, scan_number):
    patient = prediction(patient_id, scan_number)
    result = compact_patient(patient)
    result['variables'] = patient['variables']
    result['warnings'] = patient['latest_forecast']['warnings']
    result['previous_forecasts'] = [{'scan_number': item['scan_number'], 'trajectory': item['trajectory']}
                                    for item in patient['forecast_history']]
    return result


def store_prediction(patient_id, scan_number, clear_old):
    patient = prediction(patient_id, scan_number)
    target = patient_output_path(OUTPUT_DIR, patient['patient_id'], patient['name'])
    output = {'synthetic': True, 'measure': 'SLD', 'unit': 'mm', 'patients': [compact_patient(patient)]}
    with SAVE_LOCK:
        save_predictions(target, output, clear_old=clear_old)
    return {'filename': target.name, 'clear_old': clear_old}
