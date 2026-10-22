"""Fictieve opdrachtregels voor simulatie. om het uit te testen."""

IMPORTANCE = {
    'sex': 2, 'smoking': 1, 'age_years': 0, 'performance_status': 0,
    'tumor_stage': 0, 'histology': 0, 'EGFR': 0,
    'PD_L1_percent': 0, 'hemoglobin_mmol_l': 0,
}


def demo_treatment_plan(variables, synthetic=False):
    result = {'simulation_only': True, 'status': 'disabled', 'plan': None,
              'allowed_plans': [], 'alternatives': [], 'importance': dict(IMPORTANCE),
              'method': 'Fictieve beslisregels; geen MPC-optimalisatie',
              'note': 'Prioriteiten 0/1/2 zijn opdrachtwaarden, geen geschatte medische effecten.'}
    if synthetic is not True:
        return result
    sex = variables.get('sex')
    smoking = variables.get('smoking')
    if sex not in ('female', 'male') or smoking not in ('never', 'former', 'current'):
        result['status'] = 'missing_data'
        result['note'] = 'Geslacht of rookstatus ontbreekt/is onbekend; geen demo-plan.'
        return result

   #voor de demo is former roker geen roker
    is_smoker = smoking == 'current'
    candidates = [['chemo'], ['chemo', 'operatie'], ['operatie', 'chemo'], ['operatie']]
    if sex == 'female':
        sex_allowed = [['chemo'], ['chemo', 'operatie'], ['operatie', 'chemo']]
    else:
        sex_allowed = [['chemo'], ['operatie', 'chemo']]
    if is_smoker:
        smoking_allowed = [['operatie', 'chemo']]
    else:
        smoking_allowed = [['chemo'], ['chemo', 'operatie']]

    for plan in candidates:
        penalty = 0
        reasons = []
        if plan not in sex_allowed:
            penalty += IMPORTANCE['sex']
            reasons.append('Voldoet niet aan de fictieve geslachtsregel (prioriteit 2).')
        if plan not in smoking_allowed:
            penalty += IMPORTANCE['smoking']
            reasons.append('Roker: operatie dan chemo; niet-roker: chemo eerst (fictieve regel, prioriteit 1).')
        if penalty == 0:
            result['allowed_plans'].append(plan)
        else:
            result['alternatives'].append({'plan': plan, 'status': 'excluded_by_demo_rule',
                                           'rule_penalty': penalty, 'reasons': reasons})
    result['status'] = 'demo_only'
    result['plan'] = result['allowed_plans'][0]
    if is_smoker:
        result['explanation'] = 'Operatie daarna chemo volgens de fictieve rokersregel.'
    elif sex == 'female':
        result['explanation'] = 'Chemo; operatie daarna is optioneel in de vrouwelijke demo-groep.'
    else:
        result['explanation'] = 'Alleen chemo volgens de fictieve regel voor niet-rokende mannen.'
    result['smoking_interpretation'] = 'never en former: rookt nu niet; current: rookt nu.'
    return result
