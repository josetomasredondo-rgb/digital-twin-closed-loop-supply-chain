import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from .constants import FINAL_PRODUCTS


def plot_scenario_comparison(scenario_results):
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    fig.suptitle("Scenario Comparison — Decision Support System",
                 fontsize=14, fontweight="bold")

    colors = ["#1565C0", "#C62828", "#2E7D32", "#F57F17", "#6A1B9A"]
    metrics = [
        ("unmet_FP_A",    "Unmet Demand — FP_A",    "Units"),
        ("unmet_FP_B",    "Unmet Demand — FP_B",    "Units"),
        ("unmet_FP_C",    "Unmet Demand — FP_C",    "Units"),
        ("opt_cost",      "Total Cost (€)",          "€"),
        ("opt_emissions", "Total Emissions (kg CO₂)","kg CO₂"),
        ("warehouse_inv", "Warehouse Inventory",     "Units"),
        ("remanufactured_FP_A", "Remanufactured FP_A", "Units"),
        ("remanufactured_FP_B", "Remanufactured FP_B", "Units"),
        ("remanufactured_FP_C", "Remanufactured FP_C", "Units"),
    ]

    for ax, (metric, title, ylabel) in zip(axes.flat, metrics):
        for i, (name, df) in enumerate(scenario_results.items()):
            ax.plot(df["period"], df[metric],
                    label=name, color=colors[i % len(colors)],
                    linewidth=2, marker="o", markersize=3)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Period")
        ax.set_ylabel(ylabel)
        ax.legend(fontsize=6)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("scenario_comparison.png", dpi=150, bbox_inches="tight")
    print("Scenario comparison saved to: scenario_comparison.png")
    # Don't show the plot in interactive mode to avoid blocking
    # plt.show()  # Commented out to prevent blocking in script execution


def print_summary_table(scenario_results):
    print("\n" + "="*110)
    print(f"{'SCENARIO SUMMARY':^110}")
    print("="*110)
    print(f"{'Scenario':<40} {'Unmet FP_A':>10} {'Unmet FP_B':>10} {'Unmet FP_C':>10} "
          f"{'Total Cost €':>13} {'Emissions kg':>13} {'Avg SL%':>8}")
    print("-"*110)
    for name, df in scenario_results.items():
        sl = ((df["shipped_FP_A"] + df["shipped_FP_B"] + df["shipped_FP_C"]) /
              (df["demand_FP_A"]  + df["demand_FP_B"]  + df["demand_FP_C"]) * 100).mean()
        print(f"  {name:<38} {df['unmet_FP_A'].sum():>10.1f} "
              f"{df['unmet_FP_B'].sum():>10.1f} "
              f"{df['unmet_FP_C'].sum():>10.1f} "
              f"{df['opt_cost'].sum():>13.1f} "
              f"{df['opt_emissions'].sum():>13.1f} "
              f"{sl:>7.1f}%")
    print("="*110)
