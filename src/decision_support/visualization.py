import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


def print_strategy_comparison(scenario_name, strategy_dfs):
    """Print a TBL comparison table for all strategies within one scenario."""
    col_w = 32
    print(f"\n{'='*110}")
    print(f"  {scenario_name}")
    print(f"{'='*110}")
    print(
        f"  {'Strategy':<{col_w}} {'Service Level':>14} {'Total Cost €':>14} "
        f"{'Emissions kg':>14} {'Social Impact':>14} {'Unmet fp1':>10} {'Unmet fp2':>10} {'Unmet fp3':>10}"
    )
    print(f"  {'-'*col_w} {'-'*14} {'-'*14} {'-'*14} {'-'*14} {'-'*10} {'-'*10} {'-'*10}")

    for label, df in strategy_dfs.items():
        avg_sl     = df["service_level"].mean()
        total_cost = df["total_cost"].sum()
        total_emi  = df["total_emissions"].sum()
        avg_social = df["social_impact"].mean()
        unmet1     = df["unmet_fp1"].sum()
        unmet2     = df["unmet_fp2"].sum()
        unmet3     = df["unmet_fp3"].sum()
        print(
            f"  {label:<{col_w}} {avg_sl:>13.1f}% {total_cost:>14.1f} "
            f"{total_emi:>14.1f} {avg_social:>14.0f} "
            f"{unmet1:>10.1f} {unmet2:>10.1f} {unmet3:>10.1f}"
        )

    print(f"{'='*110}")


def plot_strategy_comparison(all_results):
    """
    all_results: {scenario_name: {strategy_label: df}}

    Produces one figure per disruption scenario (skips Baseline-only).
    Each figure shows 4 TBL metrics over time for each strategy.
    Saves as PNG.
    """
    metrics = [
        ("service_level",   "Service Level (%)",       "%"),
        ("total_cost",      "Total Cost (€)",           "€"),
        ("total_emissions", "Total Emissions (kg CO₂)", "kg CO₂"),
        ("social_impact",   "Social Impact (€)",        "€"),
    ]
    colors = ["#1565C0", "#C62828", "#2E7D32", "#F57F17", "#6A1B9A"]

    for scenario_name, strategy_dfs in all_results.items():
        if len(strategy_dfs) <= 1:
            continue  # nothing to compare

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f"Strategy Comparison — {scenario_name}",
                     fontsize=13, fontweight="bold")

        for ax, (metric, title, ylabel) in zip(axes.flat, metrics):
            for i, (label, df) in enumerate(strategy_dfs.items()):
                ax.plot(df["period"], df[metric],
                        label=label, color=colors[i % len(colors)],
                        linewidth=2, marker="o", markersize=3)
            ax.set_title(title, fontsize=10)
            ax.set_xlabel("Period")
            ax.set_ylabel(ylabel)
            ax.legend(fontsize=7)
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        safe = scenario_name.replace(" ", "_").replace("/", "-")[:50]
        fname = f"strategy_comparison_{safe}.png"
        plt.savefig(fname, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"Chart saved: {fname}")
