
"""Adaptieve Digital Twin en fictieve MPC-behandelsimulatie."""

from copy import deepcopy
import math
from numbers import Real

from twinning import predict
from demo_treatment_rules import demo_treatment_plan


# Volledig fictieve behandelingseffecten.
DEMO_EFFECTS = {
    "chemo": 0.9,
    "operatie": 0.55,
    "rust": 1.0,
}

DEMO_TOXICITY = {
    "chemo": 0.15,
    "operatie": 0.25,
    "rust": 0.0,
}


def valid_number(name, value, positive=False):
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(value)
    ):
        raise ValueError(f"{name} moet een eindig getal zijn")

    if value < 0 or (positive and value == 0):
        raise ValueError(
            f"{name} moet {'positief' if positive else 'niet-negatief'} zijn"
        )


def cost_function(
    trajectory,
    reference_sld,
    rule_penalty=0,
    toxicity_weight=1.0,
):
    """Fictieve optimalisatiescore, geen klinische uitkomstmaat."""

    valid_number("reference_sld", reference_sld, positive=True)
    valid_number("rule_penalty", rule_penalty)
    valid_number("toxicity_weight", toxicity_weight)

    if not trajectory:
        raise ValueError("De kostenfunctie heeft een curve nodig")

    tumor_cost = 0.0
    toxicity_cost = 0.0

    for point in trajectory:
        valid_number("sld_mm", point["sld_mm"])
        valid_number("toxicity", point["toxicity"])

        tumor_cost += point["sld_mm"] / reference_sld
        toxicity_cost += toxicity_weight * point["toxicity"]

    components = {
        "tumor": tumor_cost,
        "toxicity": toxicity_cost,
        "rules": rule_penalty,
    }

    return {
        "score": sum(components.values()),
        "components": components,
    }


def optimize_demo_plan(
    baseline,
    measurements,
    variables,
    synthetic=False,
):
    """Kies het laagst scorende fictieve behandelplan."""

    rules = demo_treatment_plan(
        variables,
        synthetic=synthetic,
    )

    result = {
        "status": "unavailable",
        "simulation_only": True,
        "plan": None,
        "next_action": None,
        "score": None,
        "trajectory": [],
        "candidates": [],
        "method": "Beperkte discrete MPC-demo",
        "reason": "Geen fictief behandelplan beschikbaar.",
    }

    if rules["status"] != "demo_only":
        return result

    if not baseline or any(
        point["median"] < 0 for point in baseline
    ):
        result["reason"] = "Geen bruikbare basiscurve."
        return result

    reference_sld = measurements[0]["sld_mm"]

    candidates = [
        {
            "plan": plan,
            "rule_penalty": 0,
            "reasons": [],
        }
        for plan in rules["allowed_plans"]
    ]

    candidates += rules["alternatives"]

    for candidate in candidates:
        plan = candidate["plan"]
        reasons = list(candidate["reasons"])

        if len(plan) > len(baseline):
            result["candidates"].append({
                "plan": plan,
                "status": "excluded",
                "reasons": reasons + ["Voorspelhorizon te kort."],
                "score": None,
            })
            continue

        factor = 1.0
        toxicity = 0.0
        previous_day = measurements[-1]["day"]
        trajectory = []

        for k, point in enumerate(baseline):
            action = plan[k] if k < len(plan) else "rust"

            duration = point["day"] - previous_day
            valid_number("intervalduur", duration, positive=True)

            effect = DEMO_EFFECTS[action]

            if action == "chemo":
                factor *= effect ** (duration / 21)
            else:
                factor *= effect

            toxicity = (
                toxicity * 0.5 ** (duration / 21)
                + DEMO_TOXICITY[action]
            )

            trajectory.append({
                "day": point["day"],
                "action": action,
                "sld_mm": point["median"] * factor,
                "toxicity": toxicity,
            })

            previous_day = point["day"]

        costs = cost_function(
            trajectory,
            reference_sld,
            candidate["rule_penalty"],
        )

        result["candidates"].append({
            "plan": plan,
            "trajectory": trajectory,
            **costs,
            "status": "excluded" if reasons else "allowed",
            "reasons": reasons,
        })

    allowed = [
        candidate
        for candidate in result["candidates"]
        if candidate["status"] == "allowed"
    ]

    if not allowed:
        result["reason"] = "Geen toegestaan behandelplan."
        return result

    best = min(
        allowed,
        key=lambda candidate: candidate["score"],
    )

    result.update({
        "status": "demo_only",
        "plan": best["plan"],
        "next_action": best["plan"][0],
        "score": best["score"],
        "components": best["components"],
        "trajectory": best["trajectory"],
        "effects": dict(DEMO_EFFECTS),
        "reason": (
            "Laagste fictieve modelscore onder "
            "de toegestane behandelvolgordes."
        ),
    })

    return result


class SLDTwin:

    def __init__(self, patient_id, variables, synthetic=False):
        self.patient_id = patient_id
        self.variables = deepcopy(variables)
        self.synthetic = synthetic
        self.measurements = []
        self.forecasts = []

    def observe_ct(self, day, sld_mm):
        valid_number("day", day)
        valid_number(
            "sld_mm",
            sld_mm,
            positive=not self.measurements,
        )

        if (
            self.measurements
            and day <= self.measurements[-1]["day"]
        ):
            raise ValueError("CT-dagen moeten oplopen")

        if sld_mm > 1000:
            raise ValueError("SLD boven modelgrens")

        self.measurements.append({
            "day": float(day),
            "sld_mm": float(sld_mm),
        })

    def forecast(
        self,
        future_days,
        *,
        n_samples=20_000,
        seed=0,
    ):
        if not self.measurements:
            raise ValueError("Voer eerst een CT-meting in")

        if (
            isinstance(n_samples, bool)
            or not isinstance(n_samples, int)
            or n_samples < 1
        ):
            raise ValueError("n_samples moet positief zijn")

        if (
            isinstance(seed, bool)
            or not isinstance(seed, int)
            or seed < 0
        ):
            raise ValueError("seed moet niet-negatief zijn")

        future_days = list(future_days)

        if not future_days:
            raise ValueError("Geen voorspeldagen opgegeven")

        previous = self.measurements[-1]["day"]

        for day in future_days:
            valid_number("future_day", day)

            if day <= previous:
                raise ValueError(
                    "Voorspeldagen moeten strikt oplopen"
                )

            previous = day

        origin = self.measurements[0]["day"]

        scan_days = [
            point["day"] - origin
            for point in self.measurements
        ]

        scan_sld = [
            point["sld_mm"]
            for point in self.measurements
        ]

        warnings = [
            "Onderzoeksdemo met fictieve behandelingseffecten.",
            "Voorspellingen bevatten onzekerheid en meetruis.",
        ]

        if len(scan_days) < 3:
            warnings.append(
                "Weinig CT-scans: modelparameters zijn onzeker."
            )

        trajectory = []

        for day in future_days:
            result = predict(
                scan_days,
                scan_sld,
                float(day) - origin,
                n_samples=n_samples,
                seed=seed,
            )

            samples = result["samples"]

            if not all(
                math.isfinite(value)
                for value in samples
            ):
                raise ValueError(
                    "Model geeft niet-eindige samples"
                )

            trajectory.append({
                "day": float(day),
                "median": result["median"],
                "p10": result["p10"],
                "p90": result["p90"],
            })

        output = {
            "patient_id": self.patient_id,
            "research_only": True,
            "model": "twinning.biexp + twinning.predict",
            "unit": "mm",
            "measure": "SLD",
            "start_day": self.measurements[-1]["day"],
            "patient_variables": deepcopy(self.variables),
            "measurements": deepcopy(self.measurements),
            "trajectory": trajectory,
            "warnings": warnings,
            "n_samples": n_samples,
            "seed": seed,
            "treatment_demo": demo_treatment_plan(
                self.variables,
                synthetic=self.synthetic,
            ),
            "treatment_optimization": optimize_demo_plan(
                trajectory,
                self.measurements,
                self.variables,
                synthetic=self.synthetic,
            ),
        }

        self.forecasts.append(deepcopy(output))
        return output


def scan_progress(
    previous_scans,
    current_scan,
    n_samples=20_000,
    seed=0,
):
    """Vergelijk CT-meting met eerdere voorspelling."""

    if not previous_scans:
        return {
            "direction": "baseline",
            "message": "Eerste CT-scan.",
        }

    previous_sld = previous_scans[-1]["sld_mm"]

    if previous_sld == 0:
        return {
            "direction": "unknown",
            "message": "Vorige SLD is nul.",
        }

    change = (
        100
        * (current_scan["sld_mm"] - previous_sld)
        / previous_sld
    )

    if change < -5:
        direction = "decreasing"
        message = "Gemeten SLD afgenomen."
    elif change > 5:
        direction = "increasing"
        message = "Gemeten SLD toegenomen."
    else:
        direction = "stable"
        message = "Gemeten SLD ongeveer gelijk."

    origin = previous_scans[0]["day"]

    prediction = predict(
        [
            scan["day"] - origin
            for scan in previous_scans
        ],
        [
            scan["sld_mm"]
            for scan in previous_scans
        ],
        current_scan["day"] - origin,
        n_samples=n_samples,
        seed=seed,
    )

    outside = not (
        prediction["p10"]
        <= current_scan["sld_mm"]
        <= prediction["p90"]
    )

    return {
        "direction": direction,
        "message": message,
        "change_percent": change,
        "previous_sld_mm": previous_sld,
        "current_sld_mm": current_scan["sld_mm"],
        "previous_baseline_prediction": {
            key: prediction[key]
            for key in ("median", "p10", "p90")
        },
        "outside_prediction_interval": outside,
        "note": (
            "Vergelijking zonder de nieuwe CT-scan "
            "in de eerdere voorspelling op te nemen."
        ),
    }


def interpolate_curve(points, day):
    """Lineaire interpolatie tussen gesimuleerde MPC-punten."""

    if not points:
        return None

    if day <= points[0]["day"]:
        return points[0]["sld_mm"]

    for left, right in zip(points[:-1], points[1:]):
        if left["day"] <= day <= right["day"]:
            fraction = (
                (day - left["day"])
                / (right["day"] - left["day"])
            )

            return (
                left["sld_mm"]
                + fraction
                * (right["sld_mm"] - left["sld_mm"])
            )

    return points[-1]["sld_mm"]


def build_full_treatment_trajectory(forecasts, step_days=7):
    """
    Bouw één adaptieve MPC-curve.

    Na iedere CT-scan begint een nieuw gesimuleerd traject.
    Historische trajecten blijven bewaard; alleen het nieuwste
    traject loopt door in de toekomst.

    Dit is een fictieve simulatie, geen behandelgeschiedenis.
    """

    if not forecasts:
        return []

    combined = []

    for index, forecast in enumerate(forecasts):
        measurements = forecast["measurements"]

        start_day = measurements[-1]["day"]
        start_sld = measurements[-1]["sld_mm"]

        optimization = forecast["treatment_optimization"]

        if optimization["status"] != "demo_only":
            return []

        treatment_curve = optimization["trajectory"]

        if not treatment_curve:
            return []

        if index + 1 < len(forecasts):
            next_forecast = forecasts[index + 1]
            end_day = next_forecast["start_day"]
        else:
            end_day = treatment_curve[-1]["day"]

        # De MPC-berekening begint bij de huidige CT-meting.
        segment = [{
            "day": start_day,
            "sld_mm": start_sld,
            "scan_number": index + 1,
            "source": "ct_initialization",
        }]

        # Simulatiepunten liggen op de MPC-horizon.
        interpolation_points = [
            {
                "day": start_day,
                "sld_mm": start_sld,
            }
        ] + treatment_curve

        # Bereken een gladder weergegeven lijn.
        current_day = start_day + step_days

        while current_day < end_day:
            # Alleen interpoleren binnen de voorspelde horizon.
            if current_day <= treatment_curve[-1]["day"]:
                value = interpolate_curve(
                    interpolation_points,
                    current_day,
                )

                segment.append({
                    "day": float(current_day),
                    "sld_mm": float(value),
                    "scan_number": index + 1,
                    "source": "mpc_simulation",
                })

            current_day += step_days

        if index + 1 < len(forecasts):
            # De nieuwe CT wordt het startpunt van de
            # volgende MPC-optimalisatie.
            # Voeg hier geen achteraf aangepaste voorspelling toe.
            pass
        else:
            # Nieuwste MPC-traject loopt door in de toekomst.
            for point in treatment_curve:
                if point["day"] > segment[-1]["day"]:
                    segment.append({
                        "day": point["day"],
                        "sld_mm": point["sld_mm"],
                        "scan_number": index + 1,
                        "source": "mpc_future",
                        "action": point["action"],
                    })

        combined.extend(segment)

    return combined


def patient_forecasts(
    patient,
    *,
    horizon=3,
    step_days=21,
    n_samples=20_000,
    seed=0,
    synthetic=False,
    scan_number=None,
):
    """Verwerk CT-scans en heroptimaliseer MPC na iedere scan."""

    if (
        isinstance(horizon, bool)
        or not isinstance(horizon, int)
        or horizon < 1
    ):
        raise ValueError("horizon moet positief zijn")

    valid_number("step_days", step_days, positive=True)

    scans = patient["ct_scans"]

    if scan_number is not None:
        if (
            isinstance(scan_number, bool)
            or not isinstance(scan_number, int)
            or not 1 <= scan_number <= len(scans)
        ):
            raise ValueError("Ongeldig scannummer")

        scans = scans[:scan_number]

    twin = SLDTwin(
        patient["id"],
        patient["variables"],
        synthetic=synthetic,
    )

    for number, scan in enumerate(scans, start=1):
        previous_scans = deepcopy(twin.measurements)

        twin.observe_ct(
            scan["day"],
            scan["sld_mm"],
        )

        days = [
            scan["day"] + step_days * k
            for k in range(1, horizon + 1)
        ]

        forecast = twin.forecast(
            days,
            n_samples=n_samples,
            seed=seed,
        )

        forecast["scan_number"] = number

        forecast["progress"] = scan_progress(
            previous_scans,
            scan,
            n_samples=n_samples,
            seed=seed,
        )

        twin.forecasts[-1] = deepcopy(forecast)

    if not twin.forecasts:
        raise ValueError("Geen CT-metingen beschikbaar")

    # Combineer de opeenvolgende fictieve MPC-simulaties.
    full_curve = build_full_treatment_trajectory(
        twin.forecasts,
        step_days=7,
    )

    latest = deepcopy(twin.forecasts[-1])

    latest["full_treatment_trajectory"] = full_curve

    latest["full_trajectory_note"] = (
        "Adaptieve fictieve MPC-simulatie. "
        "Na elke CT-scan wordt de curve opnieuw gestart "
        "en het behandelplan opnieuw geoptimaliseerd. "
        "Historische segmenten zijn geen werkelijk "
        "uitgevoerde behandelingen."
    )

    return {
        "patient_id": patient["id"],
        "name": patient["name"],
        "variables": deepcopy(patient["variables"]),
        "treatment_history": deepcopy(
            patient.get("treatment_history", [])
        ),
        "latest_forecast": latest,
        "forecast_history": deepcopy(twin.forecasts[:-1]),
    }
