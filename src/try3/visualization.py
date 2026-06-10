"""
visualization.py — DSS Output: Strategy Comparison Tables and Charts

The core DSS output is the side-by-side comparison table showing
all recovery strategies per disruption across TBL dimensions.
The decision maker reads this table and chooses which strategy to implement.
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd

from .constants import FINAL_PRODUCTS


# =============================================================================
# TERMINAL OUTPUT — DSS Comparison Table
# =============================================================================

def print_strategy_comparison(scenario_name, strategy_dfs):
    """
    Print side-by-side TBL comparison table for all strategies
    under a given disruption scenario.

    This is the core Decision Support output.
    """
    col_w = 38

    print(f"\n  {'─'*100}")
    print(f"  {'DECISION SUPPORT OUTPUT':^100}")
    print(f"  Scenario: {scenario_name}")
    print(f"  {'─'*100}")
    print(f"  {'Strategy':<{col_w}} {'Avg Service Level':>18} {'Total Cost €':>14} "
          f"{'Total Emissions':>16} {'Active Employees':>16} {'Avg Unmet':>10}")
    print(f"  {'─'*col_w} {'─'*18} {'─'*14} {'─'*16} {'─'*16} {'─'*10}")

    # Find best value per metric for highlighting
    metrics = {
        "service_level":    [],
        "total_cost":       [],
        "total_emissions":  [],
        "active_employees": [],
        "total_unmet":      [],
    }
    for label, df in strategy_dfs.items():
        metrics["service_level"].append(df["service_level"].mean())
        metrics["total_cost"].append(df["total_cost"].sum())
        metrics["total_emissions"].append(df["total_emissions"].sum())
        metrics["active_employees"].append(df["active_employees"].mean())
        metrics["total_unmet"].append(df["total_unmet"].sum())

    best_sl   = max(metrics["service_level"])
    best_cost = min(metrics["total_cost"])
    best_emi  = min(metrics["total_emissions"])
    best_empl = max(metrics["active_employees"])
    best_unmet= min(metrics["total_unmet"])

    for i, (label, df) in enumerate(strategy_dfs.items()):
        sl   = metrics["service_level"][i]
        cost = metrics["total_cost"][i]
        emi  = metrics["total_emissions"][i]
        empl = metrics["active_employees"][i]
        unmet= metrics["total_unmet"][i]

        # Mark best values with ★
        sl_mark   = " ★" if abs(sl   - best_sl)   < 0.01 else ""
        cost_mark = " ★" if abs(cost - best_cost)  < 1    else ""
        emi_mark  = " ★" if abs(emi  - best_emi)   < 0.001 else ""
        empl_mark = " ★" if abs(empl - best_empl)  < 1    else ""

        print(f"  {label:<{col_w}} "
              f"{sl:>16.1f}%{sl_mark:<2} "
              f"{cost:>13,.0f}{cost_mark:<2} "
              f"{emi:>14,.2f}{emi_mark:<2} "
              f"{empl:>14,.0f}{empl_mark:<2} "
              f"{unmet:>10,.0f}")

    print(f"  {'─'*100}")
    print(f"  ★ = best value for that metric")
    print(f"  {'─'*100}\n")


def print_summary_table(all_results):
    """Print overall summary across all scenarios."""
    print("\n" + "=" * 110)
    print(f"  {'OVERALL SIMULATION SUMMARY':^110}")
    print("=" * 110)
    print(f"  {'Scenario':<45} {'Strategy':<30} {'Avg SL%':>8} {'Total Cost':>13} {'Emissions':>12}")
    print(f"  {'─'*45} {'─'*30} {'─'*8} {'─'*13} {'─'*12}")

    for sname, strategy_dfs in all_results.items():
        for label, df in strategy_dfs.items():
            sl   = df["service_level"].mean()
            cost = df["total_cost"].sum()
            emi  = df["total_emissions"].sum()
            print(f"  {sname[:43]:<45} {label[:28]:<30} "
                  f"{sl:>7.1f}% {cost:>13,.0f} {emi:>12,.2f}")
        print(f"  {'─'*110}")

    print("=" * 110)


# =============================================================================
# CHARTS — Strategy Comparison per Scenario
# =============================================================================

def plot_strategy_comparison(all_results):
    """
    Generate a multi-panel chart showing TBL trade-offs per scenario.
    One row per disruption scenario, one column per TBL metric.
    """
    scenarios = [s for s in all_results.keys() if s != "Baseline"]
    if not scenarios:
        return

    n_scenarios = len(scenarios)
    metrics = [
        ("service_level",    "Avg Service Level (%)", "mean"),
        ("total_cost",       "Total Cost (€)",        "sum"),
        ("total_emissions",  "Total Emissions (kg)",  "sum"),
        ("active_employees", "Active Employees",      "mean"),
    ]
    n_metrics = len(metrics)

    fig, axes = plt.subplots(n_scenarios, n_metrics,
                              figsize=(5 * n_metrics, 4 * n_scenarios))
    fig.suptitle("Digital Twin DSS — Strategy Comparison by Disruption Scenario",
                 fontsize=13, fontweight="bold", y=1.01)

    if n_scenarios == 1:
        axes = [axes]

    # Undisrupted Baseline = grey (reference), No Recovery = red (disruption impact),
    # strategies A/B/C = blue/green/amber
    colors = ["#9E9E9E", "#EF5350", "#1565C0", "#2E7D32", "#F57F17"]

    for row, sname in enumerate(scenarios):
        strategy_dfs = all_results[sname]
        labels = list(strategy_dfs.keys())
        short_labels = [l[:20] for l in labels]

        for col, (metric, title, agg) in enumerate(metrics):
            ax = axes[row][col]
            values = []
            for label, df in strategy_dfs.items():
                if metric in df.columns:
                    val = df[metric].mean() if agg == "mean" else df[metric].sum()
                else:
                    val = 0.0
                values.append(val)

            bars = ax.bar(range(len(labels)), values,
                          color=colors[:len(labels)], alpha=0.85, edgecolor="white")

            # Highlight best bar
            if metric in ["service_level", "active_employees"]:
                best_idx = values.index(max(values))
            else:
                best_idx = values.index(min(values))
            bars[best_idx].set_edgecolor("gold")
            bars[best_idx].set_linewidth(2.5)

            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(short_labels, rotation=25, ha="right", fontsize=7)
            ax.set_title(title, fontsize=9, fontweight="bold")
            ax.grid(True, alpha=0.3, axis="y")
            ax.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda x, _: f"{x:,.0f}")
            )

            if col == 0:
                ax.set_ylabel(sname[:30], fontsize=8)

    plt.tight_layout()
    plt.savefig("strategy_comparison.png", dpi=150, bbox_inches="tight")
    print("\n  Chart saved: strategy_comparison.png")


def plot_period_timeseries(scenario_name, strategy_dfs, metric="service_level"):
    """
    Plot a metric over time for all strategies under one disruption.
    Useful for showing how quickly each strategy recovers.
    """
    fig, ax = plt.subplots(figsize=(12, 5))

    colors = ["#9E9E9E", "#EF5350", "#1565C0", "#2E7D32", "#F57F17"]
    for i, (label, df) in enumerate(strategy_dfs.items()):
        if label == "Undisrupted Baseline":
            style = ":"
        elif label == "No Recovery":
            style = "--"
        else:
            style = "-"
        ax.plot(df["period"], df[metric],
                label=label, color=colors[i % len(colors)],
                linewidth=2, linestyle=style, marker="o", markersize=3)

    ax.set_title(f"{scenario_name} — {metric.replace('_', ' ').title()} over Time",
                 fontsize=11, fontweight="bold")
    ax.set_xlabel("Period")
    ax.set_ylabel(metric.replace("_", " ").title())
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    fname = f"timeseries_{scenario_name[:20].replace(' ', '_')}_{metric}.png"
    plt.tight_layout()
    plt.savefig(fname, dpi=150, bbox_inches="tight")
    print(f"  Timeseries chart saved: {fname}")
    plt.close()
    