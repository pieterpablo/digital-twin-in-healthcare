
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
    Bouw 1 adaptieve MPC-curve.

    Na iedere CT-scan begint er een nieuwe simulatie.
    traject loopt door in de toekomst.

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

        # Simulatiepunten worden gebruikt voor interpolatie
        interpolation_points = [
            {
                "day": start_day,
                "sld_mm": start_sld,
            }
        ] + treatment_curve

        # Bereken een gladdere lijn
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
            # De nieuwe CT wordt het startpunt van de volgende MPC-optimalisatie
            # Voeg hier geen achteraf aangepaste voorspelling toe
            pass
        else:
            # Nieuwste MPC-traject loopt door in de toekomst
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
