# corridor-backtest

A portfolio backtesting engine focused on corridor rebalancing -- finding the optimal band widths for a given strategy. Supports multi-mode rebalancing, two-band corridor design, mean-variance optimization, 2D band search, and side-by-side strategy comparison.

![Summary Dashboard](assets/summary_dashboard.png)

## Overview

corridor-backtest simulates realistic portfolio behavior over historical price data. The core question it answers: given a portfolio's volatility and asset mix, what corridor configuration maximizes risk-adjusted performance? Each portfolio is independently configured with its own tickers, target weights, rebalancing strategy, and optional optimizer. Results are compared side by side across all strategies.

**Core features:**

- Corridor, periodic, hybrid, and no-rebalance modes
- Two-band corridor: separate inner rebalancing band and outer trigger corridor
- Band search: 1D or 2D parameter search over band/corridor widths scored by Sharpe, CAGR, Calmar, or Sortino
- Rebalance to target weights or inner band edge (minimize turnover)
- Mean-variance optimization: max Sharpe, max Sortino, min vol, equal weight
- Per-asset or lazy global weight bounds fed directly to the optimizer
- Periodic contributions with smart (fill underweight first) or pro-rata allocation
- Performance metrics: CAGR, Sharpe, Sortino, Calmar, max drawdown, rebalance frequency

**Output:**

- Equity dashboard: equity curves, drawdown, rolling Sharpe, metrics comparison, avg realized allocations
- Summary dashboard: 2D band search heatmaps with optimal parameters annotated, per-asset weight corridors showing inner band and outer corridor, rebalance event markers

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

**Band search panel (top):** 1D portfolios show score vs band width curves. 2D portfolios show a `plasma` heatmap of score across the `(inner band, corridor)` search space, with the optimal pair marked by a white star.

**Strategy summary table:** CAGR, Sharpe, max drawdown, and annualized volatility for each portfolio side by side.

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
