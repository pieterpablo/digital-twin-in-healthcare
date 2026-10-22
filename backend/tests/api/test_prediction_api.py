import json
from fastapi.testclient import TestClient
from app.main import app
from app.services import predictions as service

client = TestClient(app)


def test_search_and_scan_selection():
    patients = client.get('/api/tumor/patients').json()
    assert [p['name'] for p in patients] == ['Noor', 'Milan', 'Sara', 'Daan']
    assert all(len(p['scans']) == 4 for p in patients)
    first = client.get('/api/tumor/predict/DEMO-001?scan=1').json()
    second = client.get('/api/tumor/predict/DEMO-001?scan=2').json()
    assert len(first['latest_forecast']['measurements']) == 1
    assert len(second['latest_forecast']['measurements']) == 2
    assert first['latest_forecast']['treatment_optimization']['plan'] == second['forecast_history'][0]['treatment_optimization']['plan']


def test_invalid_requests():
    assert client.get('/api/tumor/predict/DEMO-001?scan=99').status_code == 400
    assert client.get('/api/tumor/predict/onbekend').status_code == 400
    assert client.post('/api/save', json={'patient_id': 'DEMO-001', 'scan_number': 1}).status_code == 422


def test_store_only_selected_patient(tmp_path, monkeypatch):
    monkeypatch.setattr(service, 'OUTPUT_DIR', tmp_path)
    other = client.post('/api/save', json={'patient_id': 'DEMO-004', 'scan_number': 1, 'clear_old': True}).json()
    original = (tmp_path / other['filename']).read_bytes()
    for scan, clear, history_count in [(1, True, 0), (2, False, 1), (3, True, 0)]:
        response = client.post('/api/save', json={'patient_id': 'DEMO-001', 'scan_number': scan, 'clear_old': clear})
        assert response.status_code == 200
        result = json.loads((tmp_path / response.json()['filename']).read_text(encoding='utf-8'))
        assert len(result['run_history']) == history_count
    assert (tmp_path / other['filename']).read_bytes() == original


def test_site_is_served_by_backend():
    page = client.get('/')
    assert page.status_code == 200
    assert 'zoekformulier' in page.text
    assert 'Graph.js' in page.text
    assert 'Vul een naam in om het behandeloverzicht te zien.' not in page.text
    assert client.get('/Graph.js').status_code == 200
    assert client.get('/Integration.js').status_code == 200
