# =============================================================
# VISUALIZATION
# =============================================================

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd
from .data import FINAL_PRODUCTS


def plot_results(df: pd.DataFrame):
    fig = plt.figure(figsize=(18, 14))
    fig.suptitle("Closed-Loop Supply Chain Simulation — Chemicals Industry",
                 fontsize=15, fontweight="bold", y=0.98)
    gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.50, wspace=0.35)
    periods = df["period"]

    # --- Chart 1: Demand vs Shipped per FP type ---
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(periods, df["demand_FP_A"],  label="Demand FP_A",  color="#1565C0", linewidth=2)
    ax1.plot(periods, df["shipped_FP_A"], label="Shipped FP_A", color="#42A5F5", linewidth=2, linestyle="--")
    ax1.plot(periods, df["demand_FP_B"],  label="Demand FP_B",  color="#2E7D32", linewidth=2)
    ax1.plot(periods, df["shipped_FP_B"], label="Shipped FP_B", color="#66BB6A", linewidth=2, linestyle="--")
    ax1.set_title("Demand vs Shipped — by Product")
    ax1.set_xlabel("Period"); ax1.set_ylabel("Units")
    ax1.legend(fontsize=8); ax1.grid(True, alpha=0.3)

    # --- Chart 2: Production vs Remanufacturing per FP type ---
    ax2 = fig.add_subplot(gs[0, 1])
    width = 0.2
    ax2.bar(periods - 1.5*width, df["produced_FP_A"],        width=width, label="Produced FP_A",       color="#1565C0", alpha=0.85)
    ax2.bar(periods - 0.5*width, df["remanufactured_FP_A"],  width=width, label="Remanufactured FP_A", color="#42A5F5", alpha=0.85)
    ax2.bar(periods + 0.5*width, df["produced_FP_B"],        width=width, label="Produced FP_B",       color="#2E7D32", alpha=0.85)
    ax2.bar(periods + 1.5*width, df["remanufactured_FP_B"],  width=width, label="Remanufactured FP_B", color="#66BB6A", alpha=0.85)
    ax2.set_title("Production vs Remanufacturing Output")
    ax2.set_xlabel("Period"); ax2.set_ylabel("Units")
    ax2.legend(fontsize=7); ax2.grid(True, alpha=0.3, axis="y")

    # --- Chart 3: Returns from Markets ---
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.bar(periods - 0.2, df["returns_FP_A"], width=0.4, label="Returns FP_A", color="#F57F17", alpha=0.85)
    ax3.bar(periods + 0.2, df["returns_FP_B"], width=0.4, label="Returns FP_B", color="#FFB300", alpha=0.85)
    ax3.set_title("Recovered Products Returned to Factories")
    ax3.set_xlabel("Period"); ax3.set_ylabel("Units")
    ax3.legend(fontsize=8); ax3.grid(True, alpha=0.3, axis="y")

    # --- Chart 4: Inventory Levels ---
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.plot(periods, df["supplier_inv_total"],  label="Suppliers (RM)",     linewidth=2, marker="o", markersize=3)
    ax4.plot(periods, df["factory_rm_total"],    label="Factories (RM stock)",linewidth=2, marker="s", markersize=3)
    ax4.plot(periods, df["factory_fp_total"],    label="Factories (FP stock)",linewidth=2, marker="^", markersize=3)
    ax4.plot(periods, df["factory_rp_total"],    label="Factories (RP stock)",linewidth=2, marker="D", markersize=3, linestyle="--")
    ax4.plot(periods, df["warehouse_inv_total"], label="Warehouses (FP)",     linewidth=2, marker="x", markersize=4)
    ax4.set_title("Inventory Levels Over Time")
    ax4.set_xlabel("Period"); ax4.set_ylabel("Units")
    ax4.legend(fontsize=7); ax4.grid(True, alpha=0.3)

    # --- Chart 5: Service Level per FP ---
    ax5 = fig.add_subplot(gs[2, 0])
    sl_a = (df["shipped_FP_A"] / df["demand_FP_A"] * 100).clip(upper=100)
    sl_b = (df["shipped_FP_B"] / df["demand_FP_B"] * 100).clip(upper=100)
    ax5.plot(periods, sl_a, label="Service Level FP_A", color="#1565C0", linewidth=2, marker="o", markersize=3)
    ax5.plot(periods, sl_b, label="Service Level FP_B", color="#2E7D32", linewidth=2, marker="s", markersize=3)
    ax5.axhline(y=100, color="gray", linestyle="--", linewidth=1, alpha=0.5)
    ax5.set_ylim(0, 110)
    ax5.set_title("Service Level (%) per Product")
    ax5.set_xlabel("Period"); ax5.set_ylabel("% Demand Fulfilled")
    ax5.legend(fontsize=8); ax5.grid(True, alpha=0.3)

    # --- Chart 6: Unmet Demand ---
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.bar(periods - 0.2, df["unmet_FP_A"], width=0.4, label="Unmet FP_A", color="#C62828", alpha=0.85)
    ax6.bar(periods + 0.2, df["unmet_FP_B"], width=0.4, label="Unmet FP_B", color="#EF9A9A", alpha=0.85)
    ax6.plot(periods, (df["unmet_FP_A"] + df["unmet_FP_B"]).cumsum(),
             color="#B71C1C", linewidth=2, linestyle="--", label="Cumulative Unmet (total)")
    ax6.set_title("Unmet Demand per Period")
    ax6.set_xlabel("Period"); ax6.set_ylabel("Units")
    ax6.legend(fontsize=8); ax6.grid(True, alpha=0.3, axis="y")

    plt.savefig("supply_chain_results.png", dpi=150, bbox_inches="tight")
    print("Charts saved to: supply_chain_results.png")
    plt.show()