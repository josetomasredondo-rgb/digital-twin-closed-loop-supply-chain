"""
main.py — Digital Twin DSS Entry Point

For each disruption scenario the output table shows:
    1. Undisrupted Baseline — normal operation with no disruption (reference)
    2. No Recovery          — disruption is active, manager does nothing special
    3–5. Recovery strategies A/B/C

The gap between "Undisrupted Baseline" and "No Recovery" shows the disruption
impact. The gap between "No Recovery" and each strategy shows recovery value.
"""

import sys
import io
import random
import pandas as pd

# Ensure UTF-8 output so box-drawing characters print correctly on Windows
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from .simulator import ClosedLoopSimulator, get_scenarios
from .strategies import STRATEGIES_BY_DISRUPTION, get_disruption_key
from .visualization import print_strategy_comparison, plot_strategy_comparison


def main():
    random.seed(42)
    PERIODS = 48

    scenarios   = get_scenarios()
    all_results = {}

    print("\n" + "=" * 80)
    print("  DIGITAL TWIN DECISION SUPPORT SYSTEM")
    print("  Closed-Loop Supply Chain — Scenario & Strategy Analysis")
    print("=" * 80)

    # --- Run 1: True undisrupted baseline (no disruption, no strategy) ---
    print(f"\n{'-'*80}")
    print(f"  UNDISRUPTED BASELINE (reference - no disruption)")
    print(f"{'-'*80}")
    random.seed(42)
    sim_undisrupted = ClosedLoopSimulator(
        periods=PERIODS,
        scenario={"name": "Baseline"},
        strategy=None,
        run_label="Undisrupted Baseline",
    )
    df_undisrupted = sim_undisrupted.run()
    df_undisrupted.to_csv("results_Undisrupted_Baseline.csv", index=False)

    # --- Run disruption scenarios ---
    for scenario in scenarios:
        sname = scenario["name"]
        if sname == "Baseline":
            continue  # handled above

        strategy_dfs = {}

        print(f"\n{'-'*80}")
        print(f"  SCENARIO: {sname}")
        print(f"{'-'*80}")

        # Reference: true undisrupted baseline (same df, no re-simulation)
        strategy_dfs["Undisrupted Baseline"] = df_undisrupted

        # Run 2: No Recovery — disruption active, no managerial intervention
        random.seed(42)
        sim_no_recovery = ClosedLoopSimulator(
            periods=PERIODS,
            scenario=scenario,
            strategy=None,
            run_label="No Recovery",
        )
        df_no_recovery = sim_no_recovery.run()
        strategy_dfs["No Recovery"] = df_no_recovery
        df_no_recovery.to_csv(
            f"results_{sname[:30].replace(' ', '_')}__No_Recovery.csv",
            index=False,
        )

        # Run 3/4/5: Recovery strategies for this disruption type
        dkey = get_disruption_key(sname)
        if dkey and dkey in STRATEGIES_BY_DISRUPTION:
            for strat in STRATEGIES_BY_DISRUPTION[dkey]:
                random.seed(42)
                sim = ClosedLoopSimulator(
                    periods=PERIODS,
                    scenario=scenario,
                    strategy=strat,
                )
                df = sim.run()
                strategy_dfs[strat.name] = df
                df.to_csv(
                    f"results_{sname[:30].replace(' ', '_')}__{strat.name.replace(' ', '_')}.csv",
                    index=False,
                )

        all_results[sname] = strategy_dfs
        print_strategy_comparison(sname, strategy_dfs)

    # Final summary chart across all disruption scenarios
    plot_strategy_comparison(all_results)

    print("\n" + "=" * 80)
    print("  Simulation complete. Results saved to CSV.")
    print("  Chart saved to: strategy_comparison.png")
    print("=" * 80)


if __name__ == "__main__":
    main()
