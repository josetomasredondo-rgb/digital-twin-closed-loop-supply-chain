import random
from .simulator import ClosedLoopSimulator, get_scenarios
from .strategies import STRATEGIES_BY_DISRUPTION
from .visualization import print_strategy_comparison, plot_strategy_comparison


# Disruption-type key for each scenario name (partial match)
_SCENARIO_TYPE = {
    "Supplier Failure":     "supplier_failure",
    "Demand Spike":         "demand_spike",
    "Factory 1 Downtime":   "factory_downtime",
    "Return Rate Drop":     "return_rate_drop",
}


def _disruption_key(scenario_name):
    for prefix, key in _SCENARIO_TYPE.items():
        if scenario_name.startswith(prefix):
            return key
    return None


def main():
    PERIODS = 24
    scenarios = get_scenarios()

    # results: {scenario_name: {"Baseline LP Plan": df, strategy_name: df, ...}}
    all_results = {}

    for scenario in scenarios:
        sname = scenario["name"]
        print(f"\n{'='*70}")
        print(f"SCENARIO: {sname}")
        print(f"{'='*70}")

        strategy_dfs = {}

        # Always run baseline (no strategy)
        random.seed(42)
        sim = ClosedLoopSimulator(periods=PERIODS, scenario=scenario, strategy=None)
        df  = sim.run()
        strategy_dfs["Baseline LP Plan"] = df

        # Run each recovery strategy for disruption scenarios
        dkey = _disruption_key(sname)
        if dkey and dkey in STRATEGIES_BY_DISRUPTION:
            for strat in STRATEGIES_BY_DISRUPTION[dkey]:
                random.seed(42)
                sim = ClosedLoopSimulator(periods=PERIODS, scenario=scenario, strategy=strat)
                df  = sim.run()
                strategy_dfs[strat.name] = df

        all_results[sname] = strategy_dfs
        print_strategy_comparison(sname, strategy_dfs)

        safe_name = sname.replace(" ", "_").replace("/", "-")[:40]
        for strat_label, df in strategy_dfs.items():
            safe_strat = strat_label.replace(" ", "_").replace("/", "-")[:30]
            df.to_csv(f"results_{safe_name}__{safe_strat}.csv", index=False)

    plot_strategy_comparison(all_results)


if __name__ == "__main__":
    main()
