from .constants import FINAL_PRODUCTS, RECOVERED_PRODUCTS


class RecoveryStrategy:
    """
    Defines heuristic decision rules applied during a disruption window.

    production_mode:
      "baseline"         — use the stored LP baseline plan unchanged
      "reman_first"      — exhaust remanufacturing capacity before production
      "production_first" — exhaust production capacity before remanufacturing
      "conserve"         — scale production to 50% of baseline (resource conservation)

    market_priority:
      "proportional"   — distribute available stock by demand share
      "demand_ranked"  — fill highest-demand markets first (lexicographic)

    transport_mode:
      "truck" / "air" / "sea"
    """

    def __init__(self, name, production_mode="baseline",
                 market_priority="proportional", transport_mode="truck"):
        self.name             = name
        self.production_mode  = production_mode
        self.market_priority  = market_priority
        self.transport_mode   = transport_mode

    def order_production_tasks(self, factories, baseline_prod_plan):
        """
        Returns an ordered list of ((factory_name, tech_id), qty) pairs.
        Ordering affects which technologies are saturated first when resources
        are scarce.
        """
        tasks = []
        for f in factories:
            if not f.active:
                continue
            reman_tasks = []
            prod_tasks  = []
            for tid, tech in f.technologies.items():
                qty = baseline_prod_plan.get((f.name, tid), 0.0)
                if qty <= 0:
                    qty = tech["capacity"]
                entry = ((f.name, tid), qty)
                if tech["type"] == "remanufacturing":
                    reman_tasks.append(entry)
                else:
                    prod_tasks.append(entry)

            if self.production_mode == "reman_first":
                tasks.extend(reman_tasks)
                tasks.extend(prod_tasks)
            elif self.production_mode == "production_first":
                tasks.extend(prod_tasks)
                tasks.extend(reman_tasks)
            elif self.production_mode == "conserve":
                for ((fn, tid), qty) in (prod_tasks + reman_tasks):
                    tasks.append(((fn, tid), qty * 0.5))
            else:
                tasks.extend(prod_tasks)
                tasks.extend(reman_tasks)
        return tasks

    def rank_markets(self, markets, demand_samples):
        """Return markets in the order they should be served."""
        if self.market_priority == "demand_ranked":
            return sorted(
                markets,
                key=lambda m: sum(demand_samples[m.name].get(fp, 0) for fp in FINAL_PRODUCTS),
                reverse=True,
            )
        return list(markets)


# ---------------------------------------------------------------------------
# Strategy sets per disruption type
# ---------------------------------------------------------------------------

STRATEGIES_BY_DISRUPTION = {
    "supplier_failure": [
        RecoveryStrategy(
            "A — Maximise Remanufacturing",
            production_mode="reman_first",
            market_priority="proportional",
            transport_mode="truck",
        ),
        RecoveryStrategy(
            "B — Prioritise Production",
            production_mode="production_first",
            market_priority="proportional",
            transport_mode="truck",
        ),
        RecoveryStrategy(
            "C — Accept Shortfall (ranked markets)",
            production_mode="baseline",
            market_priority="demand_ranked",
            transport_mode="truck",
        ),
    ],
    "factory_downtime": [
        RecoveryStrategy(
            "A — Air Freight Emergency",
            production_mode="production_first",
            market_priority="demand_ranked",
            transport_mode="air",
        ),
        RecoveryStrategy(
            "B — Remanufacturing Substitute",
            production_mode="reman_first",
            market_priority="proportional",
            transport_mode="truck",
        ),
        RecoveryStrategy(
            "C — Conserve & Ration",
            production_mode="conserve",
            market_priority="demand_ranked",
            transport_mode="truck",
        ),
    ],
    "demand_spike": [
        RecoveryStrategy(
            "A — Air Freight Scale-up",
            production_mode="production_first",
            market_priority="demand_ranked",
            transport_mode="air",
        ),
        RecoveryStrategy(
            "B — Sea Freight Buffer",
            production_mode="production_first",
            market_priority="proportional",
            transport_mode="sea",
        ),
        RecoveryStrategy(
            "C — Remanufacture to Fill Gap",
            production_mode="reman_first",
            market_priority="demand_ranked",
            transport_mode="truck",
        ),
    ],
    "return_rate_drop": [
        RecoveryStrategy(
            "A — Shift to Virgin Production",
            production_mode="production_first",
            market_priority="proportional",
            transport_mode="truck",
        ),
        RecoveryStrategy(
            "B — Conserve Raw Materials",
            production_mode="conserve",
            market_priority="demand_ranked",
            transport_mode="truck",
        ),
        RecoveryStrategy(
            "C — Sea Freight Cost Reduction",
            production_mode="production_first",
            market_priority="proportional",
            transport_mode="sea",
        ),
    ],
}
