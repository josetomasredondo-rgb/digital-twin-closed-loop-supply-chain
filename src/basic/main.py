"""
Closed-Loop Supply Chain Simulation - Chemicals Industry
=========================================================
Structure:
  Forward flow:  Suppliers --> Factories --> Warehouses --> Markets
  Return flow:   Markets   --> Factories  (recovered products)

Key features:
  - Multiple raw material (RM) types and final product (FP) types
  - Each factory has production technologies (RM -> FP)
    and remanufacturing technologies (RP -> FP), defined as inputs
  - Flexible routing between all echelons
  - Distance table stored for future use (costs, emissions)
  - Data collected every period and plotted at the end
"""

import random
from .data import FINAL_PRODUCTS, DISTANCE_TABLE
from .simulator import ClosedLoopSimulator
from .visualization import plot_results


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":
    random.seed(42)

    sim = ClosedLoopSimulator(periods=24)
    results_df = sim.run()

    # --- Summary statistics ---
    print("--- SUMMARY STATISTICS ---")
    for fp in FINAL_PRODUCTS:
        sl = (results_df[f"shipped_{fp}"] / results_df[f"demand_{fp}"] * 100).mean()
        print(f"  {fp} | Avg Demand: {results_df[f'demand_{fp}'].mean():.1f} | "
              f"Avg Shipped: {results_df[f'shipped_{fp}'].mean():.1f} | "
              f"Avg Service Level: {sl:.1f}% | "
              f"Total Unmet: {results_df[f'unmet_{fp}'].sum():.1f} | "
              f"Total Returns: {results_df[f'returns_{fp}'].sum():.1f} | "
              f"Total Remanufactured: {results_df[f'remanufactured_{fp}'].sum():.1f}")

    # --- Save results ---
    results_df.to_csv("supply_chain_results.csv", index=False)
    print("\nResults saved to: supply_chain_results.csv")

    # --- Distance table (stored for future use) ---
    print("\nDistance Table (km) — stored for future cost/emissions use:")
    print(DISTANCE_TABLE.to_string())

    # --- Plot ---
    plot_results(results_df)
