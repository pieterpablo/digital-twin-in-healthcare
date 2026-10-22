"""Koppeling met de ongewijzigd overgenomen modelcode."""
import json
from pathlib import Path
import sys

MODEL_DIR = Path(__file__).resolve().parents[2] / 'Algoritme_met_model'
sys.path.insert(0, str(MODEL_DIR))

from run_voorspelling import compact_patient, patient_output_path, predict_patient, save_predictions

DATA_FILE = MODEL_DIR / 'fake_patients.json'
OUTPUT_DIR = MODEL_DIR / 'voorspellingen_output'


def list_patients():
    data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
    if data.get('synthetic') is not True:
        raise ValueError('Alleen fictieve gegevens toegestaan')
    return [{'id': p['id'], 'name': p['name'], 'scans': [
        {'scan_number': i, 'day': scan['day']} for i, scan in enumerate(p['ct_scans'], 1)]}
        for p in data['patients']]


def prediction(patient_id, scan_number=None):
    patient = predict_patient(patient_id, data_file=DATA_FILE, scan_number=scan_number)
    patient['available_scans'] = next(p['scans'] for p in list_patients() if p['id'] == patient['patient_id'])
    return patient


def store_prediction(patient_id, scan_number, clear_old):
    patient = prediction(patient_id, scan_number)
    target = patient_output_path(OUTPUT_DIR, patient['patient_id'], patient['name'])
    output = {'synthetic': True, 'measure': 'SLD', 'unit': 'mm', 'patients': [compact_patient(patient)]}
    save_predictions(target, output, clear_old=clear_old)
    return {'filename': target.name, 'clear_old': clear_old}
