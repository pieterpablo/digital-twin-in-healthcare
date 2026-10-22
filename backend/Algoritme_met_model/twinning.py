import numpy as np


def biexp(t, S0, ks, kg):
    """SLD at day t.  S0 in mm,  ks and kg in 1/day."""
    with np.errstate(over="ignore"):
        s = S0 * (np.exp(-ks * t) + np.exp(kg * t) - 1.0)
    return np.clip(s, 0.0, 1000.0)


def predict(scan_days, scan_sld, t_future, n_samples=20_000, seed=0):

    rng = np.random.default_rng(seed)
    scan_days = np.asarray(scan_days, float)
    scan_sld  = np.asarray(scan_sld,  float)
    S0 = scan_sld[0]

    log_ks = rng.normal(-3.0, 0.8, n_samples)
    log_kg = rng.normal(-3.2, 0.8, n_samples)
    ks = 10 ** log_ks
    kg = 10 ** log_kg

    model_sld = biexp(scan_days[:, None], S0, ks[None, :], kg[None, :])
    sigma     = np.sqrt(2.0 ** 2 + (0.10 * model_sld) ** 2)         # 2 mm + 10 %
    loglik    = (-0.5 * ((model_sld - scan_sld[:, None]) / sigma) ** 2
                 - np.log(sigma)).sum(axis=0)
    weights   = np.exp(loglik - loglik.max())
    weights  /= weights.sum()

    future = biexp(t_future, S0, ks, kg)
    future = np.clip(future, 0, None)
    future = future + rng.normal(0, np.sqrt(2.0 ** 2 + (0.10 * future) ** 2))

    draws = rng.choice(future, size=4000, p=weights)                # keep ones that fit

    return {"median":  float(np.median(draws)),
            "p10":     float(np.quantile(draws, 0.10)),
            "p90":     float(np.quantile(draws, 0.90)),
            "samples": draws}


if __name__ == "__main__":
    scan_days = [  0,  48,  85, 132]        
    scan_sld  = [ 16,  16,  17,  20]        

    t_next = 174
    result = predict(scan_days, scan_sld, t_future=t_next)

    nadir     = min(scan_sld)
    threshold = nadir + max(0.20 * nadir, 5)       
    p_pd      = (result["samples"] >= threshold).mean()

    print(f"Scans:          {list(zip(scan_days, scan_sld))}")
    print(f"Forecast day {t_next}:  {result['median']:.1f} mm "
          f"(80 % range {result['p10']:.1f} – {result['p90']:.1f})")
    print(f"RECIST line:    {threshold:.1f} mm")
    print(f"P(progression at next scan): {p_pd:.0%}")
