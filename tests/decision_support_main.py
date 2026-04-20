import random
from tests.decision_support_simulator import ClosedLoopSimulator, get_scenarios
from tests.decision_support_visualization import plot_scenario_comparison, print_summary_table


def main():
    random.seed(42)
    PERIODS = 24

    _tmp_sim = ClosedLoopSimulator(periods=1)
    scenarios = get_scenarios(_tmp_sim.markets)

    scenario_results = {}
    for scenario in scenarios:
        random.seed(42)
        sim = ClosedLoopSimulator(periods=PERIODS, scenario=scenario)
        df = sim.run()
        scenario_results[scenario["name"]] = df
        df.to_csv(f"results_{scenario['name'].replace(' ', '_')[:30]}.csv", index=False)

    print_summary_table(scenario_results)
    plot_scenario_comparison(scenario_results)


if __name__ == "__main__":
    main()
