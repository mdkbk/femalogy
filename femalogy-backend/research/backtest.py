"""Backtest cycle-length and ovulation prediction on the Marquette FedCycleData set.

Every prediction uses only cycles BEFORE the one being predicted. Population
parameters are fitted on training women and scored on held-out women
(5-fold cross-validation by woman), so nothing is graded on data it learned from.
"""

import json
import sys
from statistics import median

import numpy as np
import pandas as pd

RNG = np.random.default_rng(7)
d = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else "data/FedCycleData071012.csv")
for c in ["LengthofCycle", "EstimatedDayofOvulation", "LengthofLutealPhase", "LengthofMenses"]:
    d[c] = pd.to_numeric(d[c], errors="coerce")
d = d.sort_values(["ClientID", "CycleNumber"])
women = {w: x for w, x in d.groupby("ClientID")}
ids = np.array(sorted(women))
RNG.shuffle(ids)
folds = np.array_split(ids, 5)
WINDOW = 6  # how many past cycles a method may look at


# ---------------- population fit (train women only) ----------------
def fit(train_ids):
    L = [women[w].LengthofCycle.dropna().to_numpy() for w in train_ids]
    L = [x for x in L if len(x) >= 2]
    allc = np.concatenate(L)
    mu = float(np.mean(allc))
    within = float(np.mean([np.var(x, ddof=1) for x in L]))  # sigma^2
    means = np.array([x.mean() for x in L])
    ns = np.array([len(x) for x in L])
    tau2 = max(0.5, float(np.var(means, ddof=1) - np.mean(within / ns)))  # method of moments
    lut = np.concatenate([women[w].LengthofLutealPhase.dropna().to_numpy() for w in train_ids])
    lut = lut[(lut >= 5) & (lut <= 20)]
    return {"mu": mu, "sigma2": within, "tau2": tau2, "luteal_median": float(np.median(lut)),
            "total_sd": float(np.std(allc))}


# ---------------- predictors: history (list of past lengths) -> predicted length ----------------
def fixed28(h, p):
    return 28.0


def current_engine(h, p):  # what Femalogy does today
    h = [x for x in h if 15 <= x <= 90][-WINDOW:]
    return float(round(median(h))) if h else 28.0


def mean_last(h, p):
    h = h[-WINDOW:]
    return float(np.mean(h)) if h else 28.0


def robust(h, p):
    """Clip each past cycle so one odd month can't drag the estimate far."""
    h = list(h[-WINDOW:])
    if not h:
        return h
    if len(h) >= 3:
        med = median(h)
        lo, hi = med - 2.5 * np.sqrt(p["sigma2"]), med + 2.5 * np.sqrt(p["sigma2"])
    else:
        lo, hi = p["mu"] - 2.5 * p["total_sd"], p["mu"] + 2.5 * p["total_sd"]
    return [min(max(x, lo), hi) for x in h]


def eb(h, p, use_robust=True):
    """Empirical Bayes: blend her average with the population average.
    Weight on her own data = n*tau2 / (n*tau2 + sigma2): grows with every cycle she logs."""
    h = robust(h, p) if use_robust else list(h[-WINDOW:])
    n = len(h)
    if n == 0:
        return p["mu"]
    w = n * p["tau2"] / (n * p["tau2"] + p["sigma2"])
    return float(w * np.mean(h) + (1 - w) * p["mu"])


def eb_median(h, p, rnd=False):
    """Same blend, but her side is her MEDIAN (one odd month barely moves it)."""
    h = split_missed(list(h), p)[-WINDOW:]
    n = len(h)
    if n == 0:
        v = p["mu"]
    else:
        w = n * p["tau2"] / (n * p["tau2"] + p["sigma2"])
        v = w * median(h) + (1 - w) * p["mu"]
    return float(round(v)) if rnd else float(v)


def eb_median_round(h, p):
    return eb_median(h, p, rnd=True)


def eb_missed_round(h, p):
    return float(round(eb_missed(h, p)))


def eb_plain(h, p):
    return eb(h, p, use_robust=False)


def split_missed(h, p):
    """A cycle about 2x her usual length is most likely a period that wasn't logged.
    Replace it with two cycles of half length (what really happened, most of the time)."""
    out = []
    for i, x in enumerate(h):
        others = [y for j, y in enumerate(h) if j != i]
        ref = median(others) if len(others) >= 2 else p["mu"]
        if 1.6 * ref <= x <= 2.4 * ref and x >= 40:
            out += [x / 2, x / 2]
        else:
            out.append(x)
    return out


def eb_missed(h, p):
    return eb(split_missed(list(h), p), p)


METHODS = {"fixed 28": fixed28, "current (median last 6)": current_engine, "mean last 6": mean_last,
           "EB plain": eb_plain, "EB robust": eb, "EB robust + missed-log": eb_missed,
           "EB robust + missed-log, whole days": eb_missed_round,
           "EB median + missed-log": eb_median, "EB median + missed-log, whole days": eb_median_round}


def bucket(n):
    return "0" if n == 0 else "1" if n == 1 else "2" if n == 2 else "3-5" if n <= 5 else "6+"


rows, ovu_rows, cover_rows = [], [], []
fits = []
for k in range(5):
    test = folds[k]
    train = np.concatenate([folds[j] for j in range(5) if j != k])
    p = fit(train)
    fits.append(p)
    for w in test:
        x = women[w]
        L = x.LengthofCycle.to_numpy()
        O = x.EstimatedDayofOvulation.to_numpy()
        LU = x.LengthofLutealPhase.to_numpy()
        for j in range(len(L)):
            if np.isnan(L[j]):
                continue
            hist = [v for v in L[:j] if not np.isnan(v)]
            # same history with one missed log (two past cycles merged) where possible
            hm = list(hist)
            if len(hm) >= 2:
                i = RNG.integers(0, len(hm) - 1)
                hm[i:i + 2] = [hm[i] + hm[i + 1]]
            for name, f in METHODS.items():
                pred = f(hist, p)
                rows.append({"method": name, "n": bucket(len(hist[-WINDOW:])), "err": pred - L[j],
                             "missed": False})
                if len(hist) >= 2:
                    rows.append({"method": name, "n": bucket(len(hm[-WINDOW:])), "err": f(hm, p) - L[j],
                                 "missed": True})
            # prediction interval for the EB robust + missed-log model
            hh = robust(split_missed(hist, p), p)
            n = len(hh)
            post_var = 1 / (1 / p["tau2"] + n / p["sigma2"]) if n else p["tau2"]
            pred = eb_missed(hist, p)
            cover_rows.append({"pred": pred, "sd": np.sqrt(p["sigma2"] + post_var), "true": L[j]})
            # ovulation day: predicted length minus a luteal length
            if not np.isnan(O[j]) and 5 <= O[j] <= 40:
                past_lut = [v for v in LU[:j] if not np.isnan(v) and 5 <= v <= 20]
                for lname, lut in [("12", 12), ("13", 13), ("14", 14),
                                   ("personal median luteal (else 13)", median(past_lut[-WINDOW:]) if past_lut else 13)]:
                    ovu_rows.append({"luteal": lname, "with": "predicted length", "err": (pred - lut) - O[j]})
                    ovu_rows.append({"luteal": lname, "with": "true length (after the fact)", "err": (L[j] - lut) - O[j]})

R = pd.DataFrame(rows)
R["abs"] = R.err.abs()


def summary(df):
    return df.groupby("method").agg(MAE=("abs", "mean"), within2=("abs", lambda a: (a <= 2).mean()),
                                    within3=("abs", lambda a: (a <= 3).mean()), N=("abs", "size")).round(3)


out = {}
clean = R[~R.missed]
print("=== Next cycle length, clean histories (held-out women) ===")
s = summary(clean).sort_values("MAE")
print(s.to_string())
out["clean_overall"] = s.reset_index().to_dict("records")

print("\n=== MAE by number of past cycles ===")
t = clean.pivot_table(index="method", columns="n", values="abs", aggfunc="mean").round(2)[["0", "1", "2", "3-5", "6+"]]
print(t.to_string())
out["by_history"] = t.reset_index().to_dict("records")

print("\n=== One past period NOT logged (two cycles merged) ===")
s2 = summary(R[R.missed]).sort_values("MAE")
print(s2.to_string())
out["missed_log"] = s2.reset_index().to_dict("records")

C = pd.DataFrame(cover_rows)
print("\n=== Prediction range for the chosen model ===")
zs = np.linspace(0.3, 2.5, 221)
cov = [((C.true >= C.pred - z * C.sd) & (C.true <= C.pred + z * C.sd)).mean() for z in zs]
z80 = float(zs[np.argmin(np.abs(np.array(cov) - 0.80))])
print(f"z for 80% real coverage: {z80:.2f}")
out["z80"] = z80
for z, label in [(0.84, "60%"), (z80, "80% (calibrated)"), (1.645, "90%")]:
    inside = ((C.true >= C.pred - z * C.sd) & (C.true <= C.pred + z * C.sd)).mean()
    print(f"nominal {label}: covers {inside:.1%} of real next periods, avg width ±{(z * C.sd).mean():.1f} days")
    out[f"coverage_{label}"] = {"covers": round(float(inside), 3), "half_width": round(float((z * C.sd).mean()), 2)}

O = pd.DataFrame(ovu_rows)
O["abs"] = O.err.abs()
print("\n=== Ovulation day: next period minus luteal length, vs measured ovulation ===")
ot = O.groupby(["with", "luteal"]).agg(MAE=("abs", "mean"), within2=("abs", lambda a: (a <= 2).mean()),
                                         bias=("err", "mean")).round(2)
print(ot.to_string())
out["ovulation"] = ot.reset_index().to_dict("records")

P = {k: round(float(np.mean([f[k] for f in fits])), 3) for k in fits[0]}
print("\n=== Population parameters (mean over folds) ===")
print(P)
out["params"] = P
json.dump(out, open("results.json", "w"), indent=2)
