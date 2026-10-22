"""CT-voorspelkoppeling en beperkte MPC-demo in SLD/mm met fictieve behandelingseffecten."""
from copy import deepcopy
import math
from numbers import Real
from twinning import predict
from demo_treatment_rules import demo_treatment_plan


# VERZONNEN GETALLENNNNN.
# Chemo: vermenigvuldig SLD met 0.9 per 21 dagen en voor operatie: eenmalig met 0.55.
DEMO_EFFECTS = {'chemo': 0.9, 'operatie': 0.55, 'rust': 1.0}
DEMO_TOXICITY = {'chemo': 0.15, 'operatie': 0.25, 'rust': 0.0}


def cost_function(trajectory, reference_sld, rule_penalty=0, toxicity_weight=1.0):
    """J = som(SLD/referentie) + wT*som(toxiciteit) + gewogen regelschendingen

    rule_penalty komt uit de demo-regels: geslacht 2, roken 1 die ik ook heb bedacht.
    Dit zijn modelkosten, geen financiële kosten of medische uitkomstmaten.
    """
    valid_number('reference_sld', reference_sld, positive=True)
    valid_number('rule_penalty', rule_penalty)
    valid_number('toxicity_weight', toxicity_weight)
    if not trajectory:
        raise ValueError('De kostenfunctie heeft een voorspelde curve nodig')
    tumor_cost = 0.0
    toxicity_cost = 0.0
    for point in trajectory:
        valid_number('sld_mm', point['sld_mm'])
        valid_number('toxicity', point['toxicity'])
        tumor_cost += point['sld_mm'] / reference_sld
        toxicity_cost += toxicity_weight * point['toxicity']
    components = {'tumor': tumor_cost, 'toxicity': toxicity_cost, 'rules': rule_penalty}
    score = sum(components.values())
    if not math.isfinite(score):
        raise ValueError('Niet-eindige score')
    return {'score': score, 'components': components}


def optimize_demo_plan(baseline, measurements, variables, synthetic=False):
    """Vergelijkt de mogelijke behandelvolgordes en berekent na elke CT-scan
opnieuw welk behandelplan de laagste kosten heeft. De voorspelling komt uit twinning.py
Met zelfgekozen waardes passen we de curve aan om het effect van chemo en operatie na te bootsen
Chemo en operatie duren in het model elk 1 tijdsinterval
Daarna wordt de rest aangevuld met rust

Het model voert geen behandelingen uit en gebruikt de echte
behandelgeschiedenis nog niet in de berekening.
    """
    rules = demo_treatment_plan(variables, synthetic=synthetic)
    result = {'status': 'unavailable', 'simulation_only': True, 'plan': None,
              'next_action': None, 'score': None, 'trajectory': [], 'candidates': [],
              'method': 'Beperkte discrete MPC-demo met fictieve behandelingseffecten',
              'reason': 'Alleen beschikbaar voor fictieve data met bekende geslacht/rookstatus.'}
    if rules['status'] != 'demo_only':
        return result
    if not baseline or any(point['median'] < 0 for point in baseline):
        result['reason'] = 'Geen bruikbare niet-negatieve basiscurve beschikbaar.'
        return result
    reference_sld = measurements[0]['sld_mm']  # Vaste schaling bij CT-updates.
    candidates = [{'plan': plan, 'rule_penalty': 0, 'reasons': []}
                  for plan in rules['allowed_plans']]
    candidates += rules['alternatives']
    for candidate in candidates:
        plan = candidate['plan']
        reasons = list(candidate['reasons'])
        if len(plan) > len(baseline):
            result['candidates'].append({'plan': plan, 'status': 'excluded',
                                          'reasons': reasons + ['Voorspelhorizon is te kort.'], 'score': None})
            continue
        factor, toxicity = 1.0, 0.0
        previous_day = measurements[-1]['day']
        trajectory = []
        for k, point in enumerate(baseline):
            action = plan[k] if k < len(plan) else 'rust'
            duration = point['day'] - previous_day
            valid_number('intervalduur', duration, positive=True)
            effect = DEMO_EFFECTS[action]
            factor *= effect ** (duration / 21) if action == 'chemo' else effect
            # Fictief herstel: halvering per 21 dagen; aanvoer per actie.
            toxicity = toxicity * 0.5 ** (duration / 21) + DEMO_TOXICITY[action]
            trajectory.append({'day': point['day'], 'action': action,
                               'sld_mm': point['median'] * factor, 'toxicity': toxicity})
            previous_day = point['day']
        costs = cost_function(trajectory, reference_sld, candidate['rule_penalty'])
        result['candidates'].append({'plan': plan, 'trajectory': trajectory, **costs,
                                      'status': 'excluded' if reasons else 'allowed', 'reasons': reasons})
    allowed = [candidate for candidate in result['candidates'] if candidate['status'] == 'allowed']
    if not allowed:
        result['reason'] = 'Geen toegestane volgorde binnen de horizon.'
        return result
    best = min(allowed, key=lambda candidate: candidate['score'])
    result.update({'status': 'demo_only', 'plan': best['plan'], 'next_action': best['plan'][0],
                   'score': best['score'], 'components': best['components'],
                   'trajectory': best['trajectory'], 'effects': dict(DEMO_EFFECTS),
                   'reason': 'Laagste modelscore onder de toegestane fictieve volgordes.'})
    return result


def valid_number(name, value, positive=False):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f'{name} moet een eindig getal zijn')
    if value < 0 or (positive and value == 0):
        raise ValueError(f'{name} moet {"positief" if positive else "niet-negatief"} zijn')


class SLDTwin:
    def __init__(self, patient_id, variables, synthetic=False):
        self.patient_id = patient_id
        self.variables = deepcopy(variables)
        self.synthetic = synthetic
        self.measurements = []
        self.forecasts = []

    def observe_ct(self, day, sld_mm):
        valid_number('day', day)
        valid_number('sld_mm', sld_mm, positive=not self.measurements)
        if self.measurements and day <= self.measurements[-1]['day']:
            raise ValueError('CT-dagen moeten strikt oplopen')
        if sld_mm > 1000:
            raise ValueError('SLD boven de 1000-mm-clip van het oorspronkelijke model')
        self.measurements.append({'day': float(day), 'sld_mm': float(sld_mm)})

    def forecast(self, future_days, *, n_samples=20_000, seed=0):
        if not self.measurements:
            raise ValueError('Voer eerst een CT-meting in')
        for name, value, minimum in [('n_samples', n_samples, 1), ('seed', seed, 0)]:
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f'{name} moet een geheel getal >= {minimum} zijn')
        future_days = list(future_days)
        if not future_days:
            raise ValueError('Geef minstens een toekomstig tijdstip')
        previous = self.measurements[-1]['day']
        for day in future_days:
            valid_number('future_day', day)
            if day <= previous:
                raise ValueError('Voorspeldagen moeten oplopen en na de laatste CT liggen')
            previous = day
        # De eerste scan is tijdstip nul voor het model.
        origin = self.measurements[0]['day']
        scan_days = [point['day'] - origin for point in self.measurements]
        scan_sld = [point['sld_mm'] for point in self.measurements]
        warnings = ['De basiscurve gebruikt alleen CT-metingen; de MPC-demo voegt fictieve effecten toe.',
                    'p10-p90: puntgewijs 80%-interval inclusief meetruis; vaste priors en 1000-mm-clip.']
        if len(scan_days) < 3:
            warnings.append('Weinig scans: beide snelheden zijn beperkt te bepalen; priors kunnen sterk doorwerken.')
        trajectory = []
        for day in future_days:
            result = predict(scan_days, scan_sld, float(day) - origin,
                             n_samples=n_samples, seed=seed)
            samples = result['samples']
            if not all(math.isfinite(value) for value in samples):
                raise ValueError('Model geeft niet-eindige voorspelsamples terug')
            if min(samples) < 0:
                warnings.append(f'Dag {day}: negatieve samples door meetruis; origineel modelresultaat behouden.')
            trajectory.append({'day': float(day), 'median': result['median'],
                               'p10': result['p10'], 'p90': result['p90']})
        output = {
            'patient_id': self.patient_id, 'research_only': True,
            'model': 'twinning.biexp + twinning.predict', 'unit': 'mm', 'measure': 'SLD',
            'start_day': self.measurements[-1]['day'],
            'patient_variables': deepcopy(self.variables),
            'measurements': deepcopy(self.measurements), 'trajectory': trajectory,
            'warnings': warnings, 'n_samples': n_samples, 'seed': seed,
            'treatment_demo': demo_treatment_plan(self.variables, synthetic=self.synthetic),
            'treatment_optimization': optimize_demo_plan(
                trajectory, self.measurements, self.variables, synthetic=self.synthetic),
        }
        self.forecasts.append(deepcopy(output))
        return output


def scan_progress(previous_scans, current_scan, n_samples=20_000, seed=0):
    """Vergelijk een nieuwe meting met de vorige meting en de oude basisvoorspeller.

    Geen klinische responsclassificatie en geen bewijs van behandelingseffect.
    De 5%-grens is uitsluitend een fictieve demotolerantie.
    """
    if not previous_scans:
        return {'direction': 'baseline', 'message': 'Eerste scan: nog geen vergelijking mogelijk.'}
    previous_sld = previous_scans[-1]['sld_mm']
    if previous_sld == 0:
        return {'direction': 'unknown', 'message': 'Vorige SLD is nul; procentuele vergelijking niet mogelijk.'}
    change = 100 * (current_scan['sld_mm'] - previous_sld) / previous_sld
    if change < -5:
        direction, message = 'decreasing', 'SLD afgenomen: kleinere gemeten tumorbelasting.'
    elif change > 5:
        direction, message = 'increasing', 'SLD toegenomen: ongunstige meettrend in deze demo.'
    else:
        direction, message = 'stable', 'SLD ongeveer gelijk binnen de fictieve 5%-tolerantie.'
    origin = previous_scans[0]['day']
    prediction = predict([scan['day'] - origin for scan in previous_scans],
                         [scan['sld_mm'] for scan in previous_scans],
                         current_scan['day'] - origin, n_samples=n_samples, seed=seed)
    outside = not prediction['p10'] <= current_scan['sld_mm'] <= prediction['p90']
    return {'direction': direction, 'message': message, 'change_percent': change,
            'previous_sld_mm': previous_sld, 'current_sld_mm': current_scan['sld_mm'],
            'previous_baseline_prediction': {key: prediction[key] for key in ('median', 'p10', 'p90')},
            'outside_prediction_interval': outside,
            'prediction_message': 'Meting buiten de eerdere puntgewijze 80%-basisvoorspelling.' if outside else
                                  'Meting binnen de eerdere puntgewijze 80%-basisvoorspelling.',
            'note': 'Vergelijking zonder de nieuwe scan te fitten; zegt niet of het demo-plan uitgevoerd of effectief is.'}


def patient_forecasts(patient, *, horizon=3, step_days=21, n_samples=20_000, seed=0, synthetic=False,
                      scan_number=None):
    """Voeg scans één voor één toe en voorspel telkens opnieuw."""
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError('horizon moet een positief geheel getal zijn')
    valid_number('step_days', step_days, positive=True)
    scans = patient['ct_scans']
    if scan_number is not None:
        if isinstance(scan_number, bool) or not isinstance(scan_number, int) or not 1 <= scan_number <= len(scans):
            raise ValueError(f'Scannummer moet tussen 1 en {len(scans)} liggen')
        scans = scans[:scan_number]  # Latere metingen nooit gebruiken.
    twin = SLDTwin(patient['id'], patient['variables'], synthetic=synthetic)
    for number, scan in enumerate(scans, start=1):
        previous_scans = deepcopy(twin.measurements)
        twin.observe_ct(scan['day'], scan['sld_mm'])
        days = [scan['day'] + step_days * k for k in range(1, horizon + 1)]
        forecast = twin.forecast(days, n_samples=n_samples, seed=seed)
        forecast['scan_number'] = number
        forecast['progress'] = scan_progress(previous_scans, scan, n_samples=n_samples, seed=seed)
        twin.forecasts[-1] = deepcopy(forecast)
    if not twin.forecasts:
        raise ValueError('Patiënt heeft geen CT-metingen')
    return {'patient_id': patient['id'], 'name': patient['name'],
            'variables': deepcopy(patient['variables']),
            'treatment_history': deepcopy(patient.get('treatment_history', [])),
            'latest_forecast': deepcopy(twin.forecasts[-1]),
            'forecast_history': deepcopy(twin.forecasts[:-1])}
