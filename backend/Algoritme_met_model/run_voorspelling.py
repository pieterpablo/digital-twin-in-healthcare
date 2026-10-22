"""Draai: python run_voorspelling.py [volledige patiëntnaam of patiëntnummer]."""
import argparse
import json
from pathlib import Path
import re
from MPC import patient_forecasts


def predict_patient(name_or_id, *, data_file=None, n_samples=20_000, scan_number=None):
    """Voorspel voor één fictieve patiënt, op naam of uniek ID."""
    if not isinstance(name_or_id, str) or not name_or_id.strip():
        raise ValueError('Geef een patiëntnaam of ID op')
    path = Path(data_file) if data_file is not None else Path(__file__).with_name('fake_patients.json')
    dataset = json.loads(path.read_text(encoding='utf-8'))
    if dataset.get('synthetic') is not True:
        raise ValueError('Deze demo-functie accepteert alleen expliciet fictieve data')
    search = name_or_id.strip().casefold()
    matches = []
    for patient in dataset['patients']:
        if search in (patient['id'].casefold(), patient['name'].casefold()):
            matches.append(patient)
    if len(matches) != 1:
        raise ValueError('Geen unieke patiënt gevonden; gebruik het unieke patiënt-ID')
    # patient_forecasts maakt een nieuwe SLDTwin: geen gedeelde historie tussen patiënten.
    return patient_forecasts(matches[0], n_samples=n_samples, synthetic=True, scan_number=scan_number)


def compact_patient(patient):
    """Bewaar één curve en korte scan-/kandidaatsamenvattingen, geen herhaalde data."""
    scans = []
    for report in patient['forecast_history'] + [patient['latest_forecast']]:
        measurement = report['measurements'][-1]
        optimization = report['treatment_optimization']
        scans.append({'scan_number': report['scan_number'], 'day': measurement['day'],
                      'sld_mm': measurement['sld_mm'], 'demo_plan': optimization['plan'],
                      'score': optimization['score'], 'progress': report['progress']})
    latest = patient['latest_forecast']
    optimization = latest['treatment_optimization']
    candidates = []
    for candidate in optimization['candidates']:
        candidates.append({key: candidate[key] for key in ('plan', 'status', 'score', 'reasons')})
    return {'patient_id': patient['patient_id'], 'name': patient['name'],
            'simulation_only': True, 'scans': scans,
            'latest_forecast': {'scan_number': latest['scan_number'], 'trajectory': latest['trajectory'],
                                'demo_plan': optimization['plan'], 'score': optimization['score'],
                                'components': optimization.get('components', {}),
                                'treatment_trajectory': optimization['trajectory'],
                                'candidates': candidates}}


def save_predictions(output_path, output, clear_old=None):
    """Bewaar uitsluitend uitvoer van één patiënt in diens eigen bestand."""
    patient = output['patients'][0]
    old_output = None
    if output_path.exists():
        old_output = json.loads(output_path.read_text(encoding='utf-8'))
        previous_runs = old_output.get('run_history', []) + [old_output]
        for run in previous_runs:
            if any(person['patient_id'] != patient['patient_id'] for person in run['patients']):
                raise ValueError('Bestand bevat een andere patiënt; wordt niet overschreven')
    if clear_old is not None and not isinstance(clear_old, bool):
        raise ValueError('clear_old moet ja/nee (boolean) zijn')
    answer = 'ja' if clear_old else 'nee'
    while clear_old is None:
        try:
            answer = input(f"Oude uitvoer van {patient['name']} ({patient['patient_id']}) verwijderen? (ja/nee): ").strip().lower()
        except EOFError:
            answer = 'nee'  # Zonder interactieve invoer blijft oude uitvoer behouden.
        if answer in ('ja', 'j', 'nee', 'n'):
            break
        print('Typ ja of nee.')
    history = []
    if answer in ('nee', 'n') and old_output is not None:
        history = old_output.pop('run_history', [])
        history.append(old_output)
    output = dict(output)
    output['run_history'] = history
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Eerst nieuwe inhoud schrijven: bij een schrijffout blijft de oude uitvoer intact.
    temporary_path = output_path.with_suffix('.json.tmp')
    temporary_path.write_text(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    temporary_path.replace(output_path)
    print('Oude uitvoer van deze patiënt vervangen.' if answer in ('ja', 'j') else
          'Oude uitvoer van deze patiënt behouden als historie.')


def patient_output_path(folder, patient_id, name):
    """Gebruik de leesbare naam plus het unieke patiënt-ID."""
    if not isinstance(patient_id, str) or re.fullmatch(r'[A-Za-z0-9_-]+', patient_id) is None:
        raise ValueError('Patiënt-ID mag alleen letters, cijfers, underscores en koppeltekens bevatten')
    safe_name = re.sub(r'[^\w-]+', '_', name.strip()).strip('_') or 'patient'
    return folder / f'voorspellingen_output_{safe_name}_{patient_id}.json'


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('patient_name_or_id', nargs='*', help='Volledige naam of patiëntnummer')
    parser.add_argument('--data', type=Path, default=root / 'fake_patients.json')
    parser.add_argument('--output-dir', '--output', dest='output_dir', type=Path,
                        default=root / 'voorspellingen_output', help='Map voor aparte patiëntbestanden')
    parser.add_argument('--n-samples', type=int, default=20_000)
    parser.add_argument('--patient', help='Voorspel alleen voor deze patiëntnaam of dit ID')
    parser.add_argument('--scan', type=int, help='Gebruik alleen metingen tot en met deze scan')
    args = parser.parse_args()
    if args.patient is not None and args.patient_name_or_id:
        parser.error('Gebruik de naam/het nummer óf --patient, niet beide')
    selected_patient = ' '.join(args.patient_name_or_id) if args.patient_name_or_id else args.patient
    scan_number = args.scan
    # Ondersteun zowel 'Noor 2' als 'Noor scan 2'. IDs blijven bijvoorbeeld DEMO-001.
    if selected_patient:
        words = selected_patient.split()
        if len(words) > 1 and words[-1].isdigit():
            if scan_number is not None:
                parser.error('Geef het scannummer eenmaal op')
            scan_number = int(words.pop())
            if words and words[-1].lower() == 'scan':
                words.pop()
            selected_patient = ' '.join(words)
    dataset = json.loads(args.data.read_text(encoding='utf-8'))
    if dataset.get('synthetic') is not True:
        raise ValueError('Dit demo-script accepteert alleen expliciet fictieve data')
    if selected_patient is not None:
        try:
            patients = [predict_patient(selected_patient, data_file=args.data, n_samples=args.n_samples,
                                        scan_number=scan_number)]
        except ValueError as error:
            parser.error(str(error))
    else:
        patients = [patient_forecasts(patient, n_samples=args.n_samples, synthetic=True, scan_number=scan_number)
                    for patient in dataset['patients']]
    patient_ids = [patient['patient_id'].casefold() for patient in patients]
    if len(set(patient_ids)) != len(patient_ids):
        parser.error('Patiënt-ID’s moeten uniek zijn')
    paths = [patient_output_path(args.output_dir, patient['patient_id'], patient['name']) for patient in patients]
    if any(path.resolve() == args.data.resolve() for path in paths):
        parser.error('Uitvoer mag het patiëntdatabestand niet overschrijven')
    for patient in patients:
        reports = patient['forecast_history'] + [patient['latest_forecast']]
        print(f"\n{patient['name']} ({patient['patient_id']}):")
        for report in reports:
            measurement = report['measurements'][-1]
            plan = report['treatment_optimization']['plan']
            print(f"  Scan {report['scan_number']} (dag {measurement['day']:g}): SLD {measurement['sld_mm']:g} mm")
            print('    Demo-plan:', ' -> '.join(plan) if plan else 'geen toegestaan plan')
            progress = report['progress']
            print('    Verloop:', progress['message'])
            if 'change_percent' in progress:
                print(f"    Verandering: {progress['change_percent']:+.1f}%")
                print('    Modelcontrole:', progress['prediction_message'])
        point = patient['latest_forecast']['trajectory'][0]
        print(f"{patient['name']}: dag {point['day']:g}, SLD {point['median']:.1f} mm "
              f"(p10-p90 {point['p10']:.1f}-{point['p90']:.1f})")
        demo = patient['latest_forecast']['treatment_demo']
        print('  Fictieve opdrachtvolgorde:', ' -> '.join(demo['plan'] or []))
        print('  Waarom:', demo.get('explanation', demo['note']))
        for alternative in demo['allowed_plans'][1:]:
            print('  Ook toegestaan:', ' -> '.join(alternative))
        optimization = patient['latest_forecast']['treatment_optimization']
        if optimization['plan'] is not None:
            print('  MPC-demo kiest:', ' -> '.join(optimization['plan']))
            print('  Kostenfunctie:', round(optimization['score'], 3), optimization['components'])
        else:
            print('  Geen MPC-demo-plan:', optimization['reason'])
    print('MPC-demo gebruikt verzonnen behandelingseffecten; geen medisch behandeladvies.')
    for patient, path in zip(patients, paths):
        output = {'synthetic': True, 'measure': 'SLD', 'unit': 'mm', 'patients': [compact_patient(patient)]}
        save_predictions(path, output)
        print(f'Voorspellingen opgeslagen: {path.resolve()}')


if __name__ == '__main__':
    main()
