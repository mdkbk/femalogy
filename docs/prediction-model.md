# How Femalogy predicts the next period

## The model

Empirical Bayes, the standard way to combine one person's few data points with what's known about everyone:

1. **Clean her history.** A cycle about twice her usual length (1.6-2.4x, and at least 40 days) is treated as a period that wasn't logged and counted as two cycles of half the length. The app also asks her: "Did a period start around [date]?" Any other single odd cycle is clipped so it can't drag the estimate far.
2. **Blend.** Estimate = w x (her average of the last 6 cycles) + (1 - w) x 29.3 days, with
   `w = n*7.79 / (n*7.79 + 9.08)` for n cycles. One cycle gives her own data 46% of the weight. Six cycles give it 84%.
3. **Range.** Next period +/- 1.03 x predictive SD. That's about +/-4 days with little data and +/-3 days with 6 cycles. Calibrated so the real date falls inside it 80% of the time.
4. **Ovulation** = next period minus 13 days, shown as a 3-day window.

Parameters live in `app/cycle/engine.py` (`POP_MEAN`, `WITHIN_VAR`, `BETWEEN_VAR`, `RANGE_Z`, `DEFAULT_LUTEAL_LENGTH`).

## Where the numbers come from

**Data:** Marquette University fertility study (Fehring and colleagues; the same group as Fehring 2006 in `sources.json`). It covers 159 women and 1,665 cycles, with ovulation measured by a hormonal fertility monitor rather than guessed. File `FedCycleData071012.csv` is widely mirrored, for example in github.com/technojam/Data-crew. It isn't committed here because its licence isn't stated.

**Method:** 5-fold cross-validation **by woman**. Parameters are fitted on 4/5 of the women and scored on the other 1/5, so nothing is graded on data it learned from. Every prediction only uses cycles before the one being predicted.

**Results (held-out women):**

| Method | Avg error, days | Within +/-2 | Within +/-3 | With one unlogged period |
|---|---|---|---|---|
| **Femalogy model** | **2.24** | **67.8%** | **80.2%** | **2.12 days** |
| Old engine (median of last 6) | 2.32 | 67.4% | 78.0% | 6.21 days |
| Mean of last 6 | 2.30 | 63.1% | 75.7% | 8.61 days |
| Always 28 days | 2.86 | 58.6% | 72.1% | 2.81 days |

Error by cycles already logged (Femalogy vs old): 0 cycles 3.05 vs 3.21, 1 cycle 2.50 vs 2.69, 2 cycles 2.14 vs 2.32, 3-5 cycles 2.23 vs 2.36, 6+ cycles 2.06 vs 2.08.

**Ovulation (vs measured ovulation day):** next period minus 13 days is off by 2.3 days on average. Minus 12 days, the old rule, is off by 2.6. Even with the true cycle length known after the fact, minus 13 is still off by 1.7 days. That's the floor for any calendar method, and it's why ovulation is always labelled an estimate and never as contraception.

**Range calibration:** the 80% range held the real next period in 80.1% of held-out cycles, with an average width of +/-3.5 days.

Re-run: `python3 research/backtest.py path/to/FedCycleData071012.csv`. The full output is in `research/results.txt`.

## Limits, said plainly

- 159 women charting for natural family planning in the US. Their cycles are likely more regular than average, and the data under-represents conditions like PCOS, perimenopause, postpartum and recent hormonal contraception.
- These are calendar predictions. Nothing here measures hormones, so being 2-3 days off is normal and expected.
- Before relying on it widely, re-fit on a larger and more diverse dataset. Femalogy's own users can provide that later, with consent. The research literature (Urteaga et al. 2021, 2 million cycles from Clue) shows the same pattern: per-user methods plus explicit handling of skipped logs work best.
