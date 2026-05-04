# corridor-backtest

A portfolio backtesting engine focused on corridor rebalancing -- finding the optimal band widths for a given strategy. Supports multi-mode rebalancing, two-band corridor design, mean-variance optimization, 2D band search, and side-by-side strategy comparison.

![Summary Dashboard](assets/summary_dashboard.png)

![Corridor Dashboard](assets/corridor_dashboard.png)

## Overview

corridor-backtest simulates portfolio behavior over historical price data. The core question it answers: given a portfolio's volatility and asset mix, what corridor configuration maximizes risk-adjusted performance? Each portfolio is independently configured with its own tickers, target weights, rebalancing strategy, and optional optimizer. Results are compared side by side across all strategies.

**Core features:**

- Corridor, periodic, hybrid, and no-rebalance modes
- Two-band corridor: separate inner rebalancing band and outer trigger corridor
- Band search: 1D or 2D parameter search with train/test split and robustness region
- Transaction costs: configurable per-trade bps applied to one-sided turnover at each rebalance
- Rebalance to target weights or inner band edge (minimize turnover)
- Mean-variance optimization: max Sharpe, max Sortino, min vol, equal weight
- Per-asset or lazy global weight bounds fed directly to the optimizer
- Periodic contributions with smart (fill underweight first) or pro-rata allocation
- Performance metrics: CAGR, Sharpe, Sortino, Calmar, max drawdown, rebalance frequency

**Output:**

- Equity dashboard: equity curves, drawdown, rolling Sharpe, metrics comparison, avg realized allocations
- Summary dashboard: 2D band search heatmaps with optimal parameters annotated, per-asset weight corridors showing inner band and outer corridor, rebalance event markers

## Key Concepts

**Corridor rebalancing** -- rebalance only when an asset weight drifts outside a defined boundary, rather than on a fixed calendar schedule. A quiet year may see no trades; a volatile year triggers several. The width of that boundary is the core tuning parameter this project optimizes.

**Band (inner band)** -- the rebalancing destination half-width. When `rebalance_to: band_edge`, trades stop at the inner band edge rather than overshooting all the way back to target. This is the range the portfolio is kept within after each rebalance event.

**Corridor (outer band)** -- the trigger boundary half-width. A rebalance fires when any weight breaches this wider limit. Separating the trigger (corridor) from the destination (band) prevents chattering: after moving to the band edge, the weight has room to drift again before triggering another rebalance.

**Absolute vs relative bands** -- absolute bands are fixed percentage-point distances from target (`target +/- band`). A 5% absolute band on a 25% target triggers at weights below 20% or above 30%, regardless of how large the target is. Relative bands scale with target weight (`target * (1 +/- band)`): a 10% relative band on a 25% target triggers at 22.5% or 27.5%, and on a 40% target triggers at 36% or 44%. Relative bands apply proportionally tighter constraints to smaller positions.

**Rebalance to target** -- restore all weights to their exact target allocations on each rebalance event. Higher turnover; the portfolio fully resets every time.

**Rebalance to band_edge** -- move only the breached asset to the nearest inner band edge, then renormalize all weights to sum to 1. Executes the minimum trade needed to exit the breach while leaving in-band assets untouched.

**Hybrid mode** -- corridor conditions are evaluated every trading day, but rebalancing only executes on a calendar schedule (monthly or quarterly) if a breach has occurred since the last rebalance. This gates corridor responsiveness behind a schedule, reducing turnover on high-volatility assets that would otherwise trigger constantly.

**Band search** -- a parameter sweep that runs a full backtest for each candidate band width and scores it by a chosen metric. To avoid in-sample overfitting, the search runs on a configurable training window (default: first 70% of dates) and the best parameters are evaluated on the held-out test period. A robustness region identifies all candidates within a threshold of the best score (default: 95%), distinguishing a stable plateau from a sharp local optimum. A 2D search sweeps `(band, corridor)` pairs jointly across all valid combinations where `corridor > band`.

**Smart contribution** -- periodic cash is directed entirely to the most underweight asset rather than split pro-rata across all holdings. Uses the contribution itself as a low-friction rebalancing tool without incurring sell-side transaction costs.

## Performance Metrics

**CAGR** (Compound Annual Growth Rate) -- total return annualized over the backtest period. `(end_value / start_value) ^ (1 / years) - 1`.

**Sharpe ratio** -- annualized excess return above the risk-free rate, divided by annualized return volatility. Measures reward per unit of total risk; penalizes both upside and downside volatility equally.

**Calmar ratio** -- CAGR divided by maximum drawdown. Rewards strategies that achieve returns without large peak-to-trough losses.

**Sortino ratio** -- like Sharpe, but uses downside deviation (volatility of negative returns only) in the denominator. Upside volatility is not penalized.

**Maximum drawdown** -- the largest peak-to-trough decline over the full backtest period, expressed as a percentage of the peak value.

## Rebalancing Modes

| Mode | Behavior |
|---|---|
| `corridor` | Rebalance immediately when any weight breaches the outer corridor |
| `periodic` | Rebalance on a fixed schedule (monthly or quarterly) |
| `hybrid` | Check corridor daily, execute only on schedule if a breach occurred |
| `none` | Buy and hold -- no rebalancing |

Corridor bands can be **absolute** (`target +/- band`) or **relative** (`target +/- band * target`).

## Two-Band Corridor Design

The rebalancing system uses two separate band widths:

- **Inner band** (`band`) -- the rebalancing destination. When `rebalance_to: band_edge`, the portfolio is moved to the nearest edge of this band, executing the minimum trade needed.
- **Outer corridor** (`corridor`) -- the trigger boundary. A rebalance fires when any weight drifts past this wider boundary.

After rebalancing to the inner band edge, the weight is well inside the outer corridor, preventing the chattering that occurs when a single band is used as both trigger and destination on high-volatility instruments.

The 2D band search finds the optimal `(band, corridor)` pair jointly, scored by a chosen metric across all valid combinations where `corridor > band`.

## Summary Dashboard

The summary dashboard has three sections:

**Band search panel (top):** 1D portfolios show score vs band width curves with the robustness region shaded. 2D portfolios show a `plasma` heatmap of score across the `(inner band, corridor)` search space; the optimal pair is marked by a white star and a dashed contour marks the robustness boundary.

**Weight corridor plots:** One block per corridor/hybrid portfolio, one subplot per asset. Each subplot shows:
- Asset weight over time (solid line)
- Target weight (dashed center line)
- Inner rebalancing band (dashed boundary + shaded fill)
- Outer corridor trigger (dotted boundary + faint shaded trigger zone)
- Rebalance events (vertical markers)

## Portfolios

Eight strategies across four themes:

**Rebalancing mode comparison** -- identical risk-parity allocation (SPY/TLT/GLD/IEF), isolating the effect of rebalancing mode:

| Portfolio | Mode | Rebalance to |
|---|---|---|
| `rp_corridor` | corridor | target |
| `rp_periodic` | periodic | target |

**Leveraged risk parity:**

| Portfolio | Assets | Mode |
|---|---|---|
| `leveraged_rp` | UPRO/TMF/GLD | corridor + 2D band search (Calmar) |

**Conservative / regime-balanced:**

| Portfolio | Assets | Mode |
|---|---|---|
| `all_weather` | SPY/TLT/IEF/GLD/DBC | hybrid, rebalance to target |

**Leveraged ETF corridor strategies** -- two-band design, `band_edge` rebalancing, Calmar-optimized via 2D search:

| Portfolio | Assets | Notes |
|---|---|---|
| `hfea` | UPRO/TMF | Classic Hedgefundie 55/45 baseline |
| `hfea_blended` | UPRO/TYD/TMF | Bond leg split between 3x 7-10yr and 3x 20+yr to reduce duration risk |
| `lev_sector` | UPRO/TQQQ/TECL/TMF | Multi-sector 3x equity with bond hedge |

**Optimized corridor:**

| Portfolio | Assets | Mode |
|---|---|---|
| `global_sharpe` | SPY/QQQ/EFA/EEM/TLT | corridor + rolling max-Sharpe optimizer + 1D band search |

## Assumptions and Limitations

- **Transaction costs** are modelled as a flat basis-point rate on one-sided turnover at each rebalance. This captures spread cost but not market impact or slippage. Liquid ETFs (SPY, TLT, GLD) use 5 bps; leveraged ETFs (UPRO, TMF, TECL) use 10 bps.
- **Band search is in-sample on the training window only.** Parameters are selected on the first 70% of dates and evaluated on the remaining 30%. Results on the test period reflect genuine out-of-sample performance given the chosen parameters, but do not account for the risk that a different train/test split would select different parameters.
- **Risk-free rate is set to 0.0** across all portfolios. This overstates Sharpe and Sortino ratios for the 2022-2024 period when the Fed Funds rate was above 4%. Configurable per portfolio via `risk_free_rate`.
- **Backtest period starts 2015**, limited by leveraged ETF inception dates. Pre-GFC stress regimes (2008-2009) are not represented.
- **No rebalancing at exact prices.** Trades execute at daily adjusted close with no bid-ask crossing or partial fill modelling.

## Quickstart

```bash
git clone https://github.com/JaredRudolph/corridor-backtest.git
cd corridor-backtest
uv run main.py
```

Results are saved to `data/processed/`. Dashboards are saved to `assets/dashboard.png` and `assets/summary_dashboard.png`.

## Configuration

All behavior is controlled through `config.py`. Each portfolio is a self-contained dict:

```python
portfolios = [
    {
        "name": "my_portfolio",
        "tickers": ["SPY", "TLT", "GLD"],
        "weights": {"SPY": 0.50, "TLT": 0.30, "GLD": 0.20},
        "benchmark": "SPY",
        "start": "2015-01-01",
        "end": None,
        "initial_capital": 10_000,
        "risk_free_rate": 0.0,
        "contribution": {
            "amount": 500,
            "frequency": "M",   # M | Q | None
            "method": "smart",  # smart | pro_rata
        },
        "rebalance": {
            "mode": "corridor",           # none | periodic | corridor | hybrid
            "threshold_type": "absolute", # absolute | relative
            "band": 0.05,                 # inner rebalancing band half-width
            "corridor": 0.15,             # outer trigger half-width (omit for single-band)
            "rebalance_to": "band_edge",  # target | band_edge
            "schedule": "Q",
            "transaction_cost_bps": 10,   # round-trip cost on one-sided turnover
        },
        "optimize": {                     # omit to use fixed weights
            "objective": "max_sharpe",    # max_sharpe | max_sortino | min_vol | equal_weight
            "weight_bounds": {"min": 0.25, "max": 1.75},
        },
        "band_search": {                  # omit to skip
            "metric": "calmar",           # sharpe | cagr | calmar | sortino
            "band_range": [0.02, 0.20],   # inner band search range
            "corridor_range": [0.04, 0.25], # outer corridor search range (enables 2D search)
            "steps": 10,                  # candidates per dimension (10 -> up to 100 pairs)
            "train_frac": 0.7,            # fraction of dates used for search; rest is test
            "robustness_threshold": 0.95, # candidates within this fraction of best are robust
        },
    },
]
```

## Project Structure

```
corridor-backtest/
├── main.py                 # entry point
├── config.py               # portfolio definitions
├── src/corridor_backtest/
│   ├── data.py             # price fetching (yfinance)
│   ├── optimize.py         # mean-variance optimizer
│   ├── rebalance.py        # corridor and schedule logic
│   ├── backtest.py         # simulation loop
│   ├── metrics.py          # CAGR, Sharpe, Calmar, Sortino, drawdown
│   ├── band_search.py      # 1D and 2D parameter search over band widths
│   ├── pipeline.py         # multi-portfolio orchestrator
│   └── plots.py            # dashboard visualization
├── tests/
├── data/
│   ├── raw/                # price cache (gitignored)
│   └── processed/          # backtest output (gitignored)
└── assets/
    ├── dashboard.png
    └── summary_dashboard.png
```

## Dependencies

- `yfinance` -- market data
- `pandas`, `numpy` -- data manipulation
- `scipy` -- portfolio optimization
- `matplotlib` -- dashboard plots
- `loguru` -- logging
- `pyarrow` -- parquet output

```bash
uv run pytest        # run tests
uv run ruff format . # format
uv run ruff check .  # lint
```
