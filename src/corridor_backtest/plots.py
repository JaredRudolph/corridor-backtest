import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

# --- Theme constants ---

BG = "#0d1117"
AXES_BG = "#161b22"
GRID = "#21262d"
TEXT = "#e6edf3"
TEXT_DIM = "#8b949e"
BORDER = "#30363d"

PALETTE = [
    "#58a6ff",  # blue
    "#3fb950",  # green
    "#ffa657",  # orange
    "#d2a8ff",  # purple
    "#f78166",  # salmon
    "#79c0ff",  # light blue
    "#56d364",  # light green
    "#ff7b72",  # coral
]

BENCHMARK_COLOR = "#8b949e"

LEGEND_STYLE = dict(
    fontsize=7,
    framealpha=0.15,
    facecolor=AXES_BG,
    edgecolor=BORDER,
    labelcolor=TEXT,
)

OUTSIDE_LEGEND = dict(
    **LEGEND_STYLE,
    loc="upper left",
    bbox_to_anchor=(1.01, 1),
    borderaxespad=0,
)


def _setup_rcparams() -> None:
    """Set global rcParams so all text contrasts with the dark background."""
    plt.rcParams["text.color"] = TEXT
    plt.rcParams["axes.labelcolor"] = TEXT_DIM
    plt.rcParams["axes.titlecolor"] = TEXT
    plt.rcParams["xtick.color"] = TEXT_DIM
    plt.rcParams["ytick.color"] = TEXT_DIM
    plt.rcParams["legend.labelcolor"] = TEXT
    plt.rcParams["figure.facecolor"] = BG
    plt.rcParams["axes.facecolor"] = AXES_BG


def _build_color_map(names: list[str]) -> dict[str, str]:
    """Map strategy names to consistent PALETTE colors by insertion order."""
    return {name: PALETTE[i % len(PALETTE)] for i, name in enumerate(names)}


def _apply_theme(fig: Figure, axes) -> None:
    """Apply the dark terminal theme to a figure and its axes."""
    fig.patch.set_facecolor(BG)

    if isinstance(axes, np.ndarray):
        ax_list = list(axes.flat)
    elif isinstance(axes, (list, tuple)):
        ax_list = list(axes)
    else:
        ax_list = [axes]

    for ax in ax_list:
        ax.set_facecolor(AXES_BG)
        ax.tick_params(colors=TEXT_DIM, labelsize=8)
        ax.xaxis.label.set_color(TEXT_DIM)
        ax.yaxis.label.set_color(TEXT_DIM)
        ax.title.set_color(TEXT)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)
        ax.grid(True, color=GRID, linewidth=0.5, linestyle="--", alpha=0.7)
        ax.set_axisbelow(True)


def plot_equity_curves(
    portfolio_data: list[dict],
    benchmark: pd.Series | None = None,
    color_map: dict[str, str] | None = None,
    axes: tuple[plt.Axes, plt.Axes] | None = None,
) -> tuple[plt.Axes, plt.Axes]:
    """Plot equity curves as two side-by-side subplots.

    Left: nominal dollar scale. Right: normalized to 1.0 at start, log scale.
    Legend shown only on the left plot. Both share the same x-axis range.
    Top 3 performers by final value are drawn full weight; others are muted.

    Args:
        portfolio_data: List of dicts with 'name' and 'results' keys.
        benchmark: Optional price series for the benchmark.
        color_map: Dict mapping strategy name to color. Built from PALETTE if None.
        axes: Tuple of (ax_nominal, ax_log). Creates a new figure if None.

    Returns:
        Tuple of (ax_nominal, ax_log).
    """
    if axes is None:
        fig, (ax_nom, ax_log) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
        _apply_theme(fig, [ax_nom, ax_log])
    else:
        ax_nom, ax_log = axes

    names = [e["name"] for e in portfolio_data]
    if color_map is None:
        color_map = _build_color_map(names)

    final_values = {
        e["name"]: e["results"]["portfolio_value"].iloc[-1] for e in portfolio_data
    }
    top3 = set(sorted(final_values, key=final_values.get, reverse=True)[:3])

    for entry in portfolio_data:
        name = entry["name"]
        color = color_map[name]
        pv = entry["results"]["portfolio_value"]
        start_val = pv.iloc[0]
        is_top = name in top3
        lw = 0.8
        alpha = 1.0 if is_top else 0.35
        zorder = 3 if is_top else 2

        ax_nom.plot(
            pv.index,
            pv.values,
            color=color,
            linewidth=lw,
            alpha=alpha,
            label=name,
            zorder=zorder,
        )
        ax_log.plot(
            pv.index,
            pv / start_val,
            color=color,
            linewidth=lw,
            alpha=alpha,
            label=name,
            zorder=zorder,
        )

        if is_top:
            log = entry["rebalance_log"]
            if not log.empty:
                rv = pv.reindex(log.index).dropna()
                for ax_ in (ax_nom, ax_log):
                    vals = rv if ax_ is ax_nom else rv / start_val
                    ax_.scatter(
                        rv.index,
                        vals,
                        color=color,
                        s=20,
                        zorder=5,
                        alpha=0.7,
                        marker="|",
                        linewidths=1.2,
                    )

    if benchmark is not None:
        ref_start = portfolio_data[0]["results"]["portfolio_value"].iloc[0]
        idx = portfolio_data[0]["results"].index
        bench_dollar = (benchmark / benchmark.iloc[0] * ref_start).reindex(
            idx, method="ffill"
        )
        bench_norm = bench_dollar / ref_start

        for ax_, vals in ((ax_nom, bench_dollar), (ax_log, bench_norm)):
            ax_.plot(
                vals.index,
                vals.values,
                color=BENCHMARK_COLOR,
                linewidth=0.8,
                linestyle="--",
                alpha=0.5,
                zorder=1,
                label="Benchmark" if ax_ is ax_nom else "_nolegend_",
            )

    ax_nom.set_title("Portfolio Value ($)")
    ax_nom.set_ylabel("Value ($)")
    ax_nom.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_nom.legend(**LEGEND_STYLE)

    ax_log.set_title("Growth Multiple (log scale)")
    ax_log.set_ylabel("Growth Multiple")
    ax_log.set_yscale("log")
    ax_log.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}x"))
    ax_log.legend(**LEGEND_STYLE)

    return ax_nom, ax_log


def plot_drawdown(
    portfolio_data: list[dict],
    color_map: dict[str, str] | None = None,
    ax: plt.Axes | None = None,
) -> plt.Axes:
    """Plot underwater drawdown chart for all portfolios.

    Args:
        portfolio_data: List of dicts with 'name' and 'results' keys.
        color_map: Dict mapping strategy name to color. Built from PALETTE if None.
        ax: Axes to plot on. Creates a new figure if None.

    Returns:
        The Axes with drawdown series drawn.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 3))
        _apply_theme(fig, ax)

    names = [e["name"] for e in portfolio_data]
    if color_map is None:
        color_map = _build_color_map(names)

    for entry in portfolio_data:
        name = entry["name"]
        color = color_map[name]
        pv = entry["results"]["portfolio_value"]
        peak = pv.cummax()
        drawdown = (pv - peak) / peak
        ax.plot(drawdown.index, drawdown.values, color=color, linewidth=0.8, label=name)
        ax.fill_between(drawdown.index, drawdown.values, 0, color=color, alpha=0.08)

    ax.axhline(0, color=BORDER, linewidth=0.8)
    ax.set_title("Drawdown")
    ax.set_ylabel("Drawdown")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0%}"))
    ax.legend(**OUTSIDE_LEGEND)

    return ax


def plot_rolling_sharpe(
    portfolio_data: list[dict],
    window: int = 252,
    risk_free_rate: float = 0.0,
    color_map: dict[str, str] | None = None,
    ax: plt.Axes | None = None,
) -> plt.Axes:
    """Plot rolling annualized Sharpe ratio. Legend placed outside the axes.

    Args:
        portfolio_data: List of dicts with 'name' and 'results' keys.
        window: Rolling window in trading days. Default is 252 (1 year).
        risk_free_rate: Annualized risk-free rate.
        color_map: Dict mapping strategy name to color. Built from PALETTE if None.
        ax: Axes to plot on. Creates a new figure if None.

    Returns:
        The Axes with rolling Sharpe series drawn.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 3))
        _apply_theme(fig, ax)

    names = [e["name"] for e in portfolio_data]
    if color_map is None:
        color_map = _build_color_map(names)

    daily_rf = risk_free_rate / 252

    for entry in portfolio_data:
        name = entry["name"]
        color = color_map[name]
        pv = entry["results"]["portfolio_value"]
        excess = pv.pct_change().dropna() - daily_rf
        rolling = (
            excess.rolling(window).mean() / excess.rolling(window).std() * np.sqrt(252)
        )
        ax.plot(rolling.index, rolling.values, color=color, linewidth=0.8, label=name)

    ax.axhline(0, color=BORDER, linewidth=0.8)
    ax.axhline(1, color=TEXT_DIM, linewidth=0.5, linestyle=":", alpha=0.5)
    ax.set_title(f"Rolling Sharpe ({window}d)")
    ax.set_ylabel("Sharpe")

    # Single legend placed outside -- do not call ax.legend() anywhere else
    ax.legend(**OUTSIDE_LEGEND)

    return ax


def plot_metrics_comparison(
    comparison: pd.DataFrame,
    color_map: dict[str, str] | None = None,
    axes: list[plt.Axes] | None = None,
) -> list[plt.Axes]:
    """Plot per-metric horizontal bar charts sorted by value.

    Args:
        comparison: DataFrame with one row per portfolio from pipeline.run_pipeline.
        color_map: Dict mapping strategy name to color. Built from PALETTE if None.
        axes: List of 4 Axes. Creates a 2x2 figure if None.

    Returns:
        List of the 4 Axes used.
    """
    metrics = [
        ("cagr", "CAGR", "{:.1%}"),
        ("sharpe", "Sharpe", "{:.2f}"),
        ("calmar", "Calmar", "{:.2f}"),
        ("max_drawdown", "Max Drawdown", "{:.1%}"),
    ]

    names = comparison.index.tolist()
    if color_map is None:
        color_map = _build_color_map(names)

    if axes is None:
        fig, ax_grid = plt.subplots(2, 2, figsize=(10, 7))
        _apply_theme(fig, ax_grid)
        axes = list(ax_grid.flat)

    for ax, (col, title, fmt) in zip(axes, metrics):
        raw = comparison[col]
        order = raw.argsort()
        sorted_names = [names[i] for i in order]
        sorted_values = raw.iloc[order].values
        sorted_colors = [color_map[n] for n in sorted_names]

        y = np.arange(len(sorted_names))
        ax.barh(y, sorted_values, color=sorted_colors, height=0.6, alpha=0.85)

        ax.set_yticks(y)
        ax.set_yticklabels(sorted_names, fontsize=7)
        ax.set_title(title)
        ax.axvline(0, color=BORDER, linewidth=0.8)

        x_lo, x_hi = ax.get_xlim()
        x_range = x_hi - x_lo
        if col == "max_drawdown":
            ax.set_xlim(left=sorted_values.min() * 1.15)
        else:
            ax.set_xlim(x_lo, x_hi + x_range * 0.28)

        for val, yi in zip(sorted_values, y):
            if np.isfinite(val):
                if col == "max_drawdown":
                    ax.text(
                        val - 0.005,
                        yi,
                        fmt.format(val),
                        va="center",
                        ha="right",
                        fontsize=7,
                        color=TEXT_DIM,
                    )
                else:
                    ax.text(
                        val + x_range * 0.015,
                        yi,
                        fmt.format(val),
                        va="center",
                        ha="left",
                        fontsize=7,
                        color=TEXT_DIM,
                    )

    return list(axes)


def plot_band_search_curves(
    portfolio_data: list[dict],
    color_map: dict[str, str] | None = None,
    ax: plt.Axes | None = None,
) -> plt.Axes:
    """Plot band search score curves for all portfolios that ran a band search.

    Each curve shows metric score vs band width with the optimal point marked.
    A secondary y-axis shows rebalance count vs band width.

    Args:
        portfolio_data: List of dicts with 'name', 'band_search_results', 'config' keys.
        color_map: Dict mapping strategy name to color. Built from PALETTE if None.
        ax: Axes to plot on. Creates a new figure if None.

    Returns:
        The Axes with score curves drawn.
    """
    entries = [e for e in portfolio_data if e.get("band_search_results") is not None]

    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 4))
        _apply_theme(fig, ax)

    names = [e["name"] for e in portfolio_data]
    if color_map is None:
        color_map = _build_color_map(names)

    for entry in entries:
        name = entry["name"]
        color = color_map[name]
        df = entry["band_search_results"].sort_values("band")
        metric = df["metric"].iloc[0]

        ax.plot(df["band"], df["score"], color=color, linewidth=1.2, label=name)

        best = df.loc[df["score"].idxmax()]
        ax.scatter(
            [best["band"]],
            [best["score"]],
            color=color,
            s=50,
            zorder=5,
        )
        ax.annotate(
            f"{best['band']:.3f}",
            xy=(best["band"], best["score"]),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=6,
            color=color,
        )

    ax.set_title(f"Band Search: {metric.capitalize()} vs Band Width")
    ax.set_xlabel("Band Width")
    ax.set_ylabel(metric.capitalize())
    ax.legend(**OUTSIDE_LEGEND)

    return ax


def plot_weight_corridors(
    entry: dict,
    color_map: dict[str, str] | None = None,
    axes: list[plt.Axes] | None = None,
) -> list[plt.Axes]:
    """Plot weight over time with shaded corridor bands for a single portfolio.

    One subplot per asset. Shaded region shows the corridor band around target.
    Vertical lines mark rebalance events.

    Args:
        entry: Single portfolio_data dict with 'results', 'rebalance_log', 'config'.
        color_map: Dict mapping ticker to color. Built from asset_palette if None.
        axes: List of Axes, one per ticker. Creates a new figure if None.

    Returns:
        List of Axes, one per ticker.
    """
    config = entry["config"]
    results = entry["results"]
    rebalance_log = entry["rebalance_log"]
    targets = config["weights"]
    band = config["rebalance"]["band"]
    threshold_type = config["rebalance"]["threshold_type"]

    # derive tickers from weight columns so this works for any portfolio
    tickers = [c.replace("_weight", "") for c in results.columns if c.endswith("_weight")]

    asset_palette = [
        "#f0c040", "#58a6ff", "#3fb950", "#ffa657",
        "#d2a8ff", "#f78166", "#79c0ff", "#56d364",
    ]
    if color_map is None:
        color_map = {t: asset_palette[i % len(asset_palette)] for i, t in enumerate(tickers)}

    n = len(tickers)
    if axes is None:
        fig, ax_arr = plt.subplots(n, 1, figsize=(14, 2.2 * n), sharex=True)
        _apply_theme(fig, ax_arr)
        axes = list(ax_arr) if n > 1 else [ax_arr]

    # print raw diagnostics per asset before any transformation
    weight_cols = [f"{t}_weight" for t in tickers]
    for ticker, col in zip(tickers, weight_cols):
        raw = results[col]
        print(
            f"[{entry['name']}] {ticker} raw weight: "
            f"min={raw.min():.4f} max={raw.max():.4f} "
            f"mean={raw.mean():.4f} std={raw.std():.4f}"
        )

    # normalize row-wise if any row sum deviates from 1.0 by more than 0.01
    weight_matrix = results[weight_cols]
    row_sums = weight_matrix.sum(axis=1)
    if (row_sums - 1.0).abs().max() > 0.01:
        print(f"[{entry['name']}] row sums deviate from 1.0 -- normalizing")
        weight_matrix = weight_matrix.div(row_sums, axis=0)

    has_dynamic_targets = f"{tickers[0]}_target" in results.columns

    for ax, ticker in zip(axes, tickers):
        color = color_map[ticker]
        col = f"{ticker}_weight"
        weights = weight_matrix[col].clip(0, 1)

        if has_dynamic_targets:
            target_series = results[f"{ticker}_target"]
        else:
            target_series = pd.Series(targets[ticker], index=results.index)

        if threshold_type == "relative":
            lo = target_series * (1 - band)
            hi = target_series * (1 + band)
        else:
            lo = target_series - band
            hi = target_series + band

        ax.plot(weights.index, weights.values, color=color, linewidth=0.8, label=ticker)
        ax.plot(target_series.index, target_series.values, color=color,
                linewidth=0.6, linestyle="--", alpha=0.6)
        ax.fill_between(weights.index, lo, hi, color=color, alpha=0.10)
        ax.plot(lo.index, lo.values, color=color, linewidth=0.4, linestyle=":", alpha=0.4)
        ax.plot(hi.index, hi.values, color=color, linewidth=0.4, linestyle=":", alpha=0.4)

        if not rebalance_log.empty:
            for date in rebalance_log.index:
                ax.axvline(date, color=TEXT_DIM, linewidth=0.4, alpha=0.4)

        ax.set_ylabel(ticker, fontsize=8)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0%}"))
        ax.legend(fontsize=7, loc="upper right", framealpha=0.2,
                  facecolor=AXES_BG, edgecolor=BORDER, labelcolor=TEXT)

    axes[0].set_title(f"Weight Corridors: {entry['name']}")

    return axes


def plot_avg_allocations(
    comparison: pd.DataFrame,
    ax: plt.Axes | None = None,
) -> plt.Axes:
    """Plot average realized portfolio allocations as stacked horizontal bars.

    One row per portfolio. Asset legend placed below the chart.

    Args:
        comparison: DataFrame with one row per portfolio from pipeline.run_pipeline.
            Must contain '{ticker}_avg_weight' columns.
        ax: Axes to plot on. Creates a new figure if None.

    Returns:
        The Axes with allocations drawn.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(16, 7))
        _apply_theme(fig, ax)

    weight_cols = [c for c in comparison.columns if c.endswith("_avg_weight")]
    tickers = [c.replace("_avg_weight", "") for c in weight_cols]

    asset_palette = [
        "#f0c040",
        "#58a6ff",
        "#3fb950",
        "#ffa657",
        "#d2a8ff",
        "#f78166",
        "#79c0ff",
        "#56d364",
        "#ff7b72",
        "#b3f0b3",
    ]
    ticker_colors = {
        t: asset_palette[i % len(asset_palette)] for i, t in enumerate(tickers)
    }

    names = comparison.index.tolist()
    n = len(names)
    # One y-position per strategy with enough spacing
    y = np.arange(n)

    lefts = np.zeros(n)
    handles = []
    for ticker, col in zip(tickers, weight_cols):
        values = comparison[col].fillna(0).values
        bars = ax.barh(
            y,
            values,
            left=lefts,
            height=0.6,
            color=ticker_colors[ticker],
            alpha=0.9,
        )
        handles.append(bars[0])
        for j in range(n):
            val = values[j]
            if val > 0.04:
                ax.text(
                    lefts[j] + val / 2,
                    y[j],
                    f"{val:.0%}",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color=BG,
                    fontweight="bold",
                )
        lefts += values

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0%}"))
    ax.set_title("Avg Realized Allocations")

    # Asset legend forced into a single row below the chart
    ax.legend(
        handles,
        tickers,
        fontsize=8,
        framealpha=0.15,
        facecolor=AXES_BG,
        edgecolor=BORDER,
        labelcolor=TEXT,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.08),
        ncol=len(tickers),
        borderaxespad=0,
    )

    return ax


def plot_corridor_dashboard(
    portfolio_data: list[dict],
    output_path: str | None = None,
) -> Figure:
    """Assemble the corridor methodology dashboard.

    Layout:
      Row 0: Band search score curves (full width)
      Row 1: Summary stats table
      Rows 2+: Weight corridor subplots for each corridor/hybrid portfolio

    Args:
        portfolio_data: List of dicts with 'name', 'results', 'rebalance_log',
            'band_search_results', 'config' keys.
        output_path: If provided, saves the figure to this path.

    Returns:
        The assembled Figure.
    """
    _BAND_HEIGHT = 4.0       # inches for band search panel
    _TABLE_ROW_HEIGHT = 0.55  # inches per row in summary table (header + data rows)
    _SUBPLOT_HEIGHT = 3.5    # inches per asset subplot

    _setup_rcparams()

    corridor_modes = {"corridor", "hybrid"}
    corridor_entries = [
        e for e in portfolio_data
        if e["config"]["rebalance"]["mode"] in corridor_modes
    ]

    ticker_counts = [len(e["config"]["tickers"]) for e in corridor_entries]
    corridor_rows = sum(ticker_counts)
    n_portfolios = len(portfolio_data)

    # table height scales with number of portfolio rows (+1 for header)
    table_height = (1 + n_portfolios) * _TABLE_ROW_HEIGHT
    total_height = _BAND_HEIGHT + table_height + _SUBPLOT_HEIGHT * corridor_rows

    band_ratio = _BAND_HEIGHT / _SUBPLOT_HEIGHT
    table_ratio = table_height / _SUBPLOT_HEIGHT
    height_ratios = [band_ratio, table_ratio] + ticker_counts
    total_rows = 2 + len(corridor_entries)

    fig = plt.figure(figsize=(14, total_height))
    fig.patch.set_facecolor(BG)

    gs = fig.add_gridspec(
        total_rows,
        1,
        height_ratios=height_ratios,
        hspace=0.50,
        left=0.10,
        right=0.88,
        top=0.94,
        bottom=0.04,
    )

    names = [e["name"] for e in portfolio_data]
    color_map = _build_color_map(names)

    # Row 0: band search curves
    ax_band = fig.add_subplot(gs[0])
    _apply_theme(fig, ax_band)
    plot_band_search_curves(portfolio_data, color_map=color_map, ax=ax_band)

    # Row 1: summary stats table derived from results
    ax_table = fig.add_subplot(gs[1])
    _apply_theme(fig, ax_table)
    ax_table.set_axis_off()

    col_labels = ["CAGR", "Sharpe", "Max DD", "Ann. Vol"]
    row_labels, cell_text = [], []
    for entry in portfolio_data:
        pv = entry["results"]["portfolio_value"]
        daily_ret = pv.pct_change().dropna()
        years = (pv.index[-1] - pv.index[0]).days / 365.25
        p_cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
        std = daily_ret.std()
        p_sharpe = float(daily_ret.mean() / std * np.sqrt(252)) if std > 0 else float("nan")
        peak = pv.cummax()
        p_maxdd = float(((pv - peak) / peak).min())
        ann_vol = std * np.sqrt(252)
        row_labels.append(entry["name"])
        cell_text.append([
            f"{p_cagr:.1%}", f"{p_sharpe:.2f}", f"{p_maxdd:.1%}", f"{ann_vol:.1%}",
        ])

    tbl = ax_table.table(
        cellText=cell_text, rowLabels=row_labels, colLabels=col_labels, loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.auto_set_column_width(list(range(len(col_labels))))
    row_scale = max(2.5, 10.0 / max(n_portfolios, 1))
    tbl.scale(1, row_scale)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_facecolor(AXES_BG if r > 0 else BG)
        cell.set_edgecolor(TEXT_DIM)
        cell.set_linewidth(0.8)
        cell.set_text_props(color=TEXT if r > 0 else TEXT_DIM)
    ax_table.set_title("Strategy Summary", color=TEXT, fontsize=10, pad=6)

    # Rows 2+: one weight-corridor block per corridor portfolio
    for i, entry in enumerate(corridor_entries):
        n = len(entry["config"]["tickers"])
        gs_inner = gs[2 + i].subgridspec(n, 1, hspace=0.15)
        axes = [fig.add_subplot(gs_inner[j]) for j in range(n)]
        _apply_theme(fig, axes)
        plot_weight_corridors(entry, axes=axes)

    fig.text(
        0.10, 0.997,
        "Corridor Optimization Dashboard",
        color=TEXT, fontsize=14, fontweight="bold", va="top",
    )

    if output_path is not None:
        fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=BG)

    return fig


def plot_dashboard(
    comparison: pd.DataFrame,
    portfolio_data: list[dict],
    benchmark: pd.Series | None = None,
    output_path: str | None = None,
) -> Figure:
    """Assemble the full tear sheet dashboard.

    Layout:
      Row 0: Equity curves (left) | Metrics 2x2 (right)
      Row 1: Drawdown (full width)
      Row 2: Rolling Sharpe (full width)
      Row 3: Final allocations (full width, taller)

    Args:
        comparison: DataFrame with one row per portfolio from pipeline.run_pipeline.
        portfolio_data: List of dicts with 'name', 'results', 'rebalance_log'.
        benchmark: Optional benchmark price series for the equity curve.
        output_path: If provided, saves the figure to this path.

    Returns:
        The assembled Figure.
    """
    _setup_rcparams()

    names = [e["name"] for e in portfolio_data]
    color_map = _build_color_map(names)

    fig = plt.figure(figsize=(14, 24))
    fig.patch.set_facecolor(BG)

    gs = fig.add_gridspec(
        6,
        2,
        height_ratios=[3, 3, 2, 1.5, 1.5, 3],
        hspace=0.40,
        wspace=0.45,
        left=0.10,
        right=0.88,
        top=0.94,
        bottom=0.07,
    )

    # Rows 0-1: equity curves stacked vertically, full width each
    ax_equity_nom = fig.add_subplot(gs[0, :])
    ax_equity_log = fig.add_subplot(gs[1, :])

    # Row 2: metrics 2x2
    gs_metrics = gs[2, :].subgridspec(2, 2, hspace=0.7, wspace=0.5)
    axes_metrics = [
        fig.add_subplot(gs_metrics[i, j]) for i in range(2) for j in range(2)
    ]

    # Row 3: drawdown full width
    ax_drawdown = fig.add_subplot(gs[3, :])

    # Row 4: rolling sharpe full width
    ax_rolling = fig.add_subplot(gs[4, :])

    # Row 5: final allocations full width
    ax_alloc = fig.add_subplot(gs[5, :])

    all_axes = [
        ax_equity_nom,
        ax_equity_log,
        ax_drawdown,
        ax_rolling,
        ax_alloc,
    ] + axes_metrics
    _apply_theme(fig, all_axes)

    plot_equity_curves(
        portfolio_data,
        benchmark=benchmark,
        color_map=color_map,
        axes=(ax_equity_nom, ax_equity_log),
    )
    plot_metrics_comparison(comparison, color_map=color_map, axes=axes_metrics)
    plot_drawdown(portfolio_data, color_map=color_map, ax=ax_drawdown)
    plot_rolling_sharpe(portfolio_data, color_map=color_map, ax=ax_rolling)
    plot_avg_allocations(comparison, ax=ax_alloc)

    start = portfolio_data[0]["results"].index[0].strftime("%Y-%m-%d")
    end = portfolio_data[0]["results"].index[-1].strftime("%Y-%m-%d")

    fig.text(
        0.10,
        0.997,
        "Portfolio Backtest Dashboard",
        color=TEXT,
        fontsize=14,
        fontweight="bold",
        va="top",
    )
    fig.text(
        0.10,
        0.990,
        f"{' | '.join(names)}     {start} to {end}",
        color=TEXT_DIM,
        fontsize=7,
        va="top",
    )

    if output_path is not None:
        fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=BG)

    return fig
