"""
strategies.py — Recovery Strategy Definitions for the Digital Twin DSS

FIX: get_production_tasks() now returns REPLACEMENT quantities for the
disruption window rather than additive quantities. The baseline plan is
used only as a reference ceiling, not as a floor to build on top of.

FIX: Return Rate Drop strategies A and C are now genuinely different:
  A — Shift to Virgin Production (production_first, no safety stock)
  B — Conserve Raw Materials    (conserve, demand_ranked)
  C — Sea Freight + Safety Stock (production_first, sea transport, safety_stock_draw)
  C was previously identical to A (both truck, proportional). Sea freight is
  now the distinguishing dimension so the TBL trade-off is meaningful.
"""


class RecoveryStrategy:
    """
    Defines the operational rules applied during a disruption window.
    Strategy logic REPLACES baseline flows during disruption periods.
    """

    def __init__(self, name,
                 production_mode="baseline",
                 market_priority="proportional",
                 transport_mode="truck",
                 remanufacturing_boost=1.0,
                 safety_stock_draw=False):
        self.name = name
        self.production_mode = production_mode
        self.market_priority = market_priority
        self.transport_mode = transport_mode
        self.remanufacturing_boost = remanufacturing_boost
        self.safety_stock_draw = safety_stock_draw

    def get_production_tasks(self, factories, baseline_prod_plan):
        """
        Return ordered list of (factory_name, tech_id, quantity) tuples.

        FIX: quantities here are REPLACEMENT targets for the disruption
        period — the simulator must use ONLY these tasks when disruption
        is active, not run them in addition to the baseline tasks.

        Quantities are capped at the technology's per-period capacity
        (not inflated beyond physical limits).
        """
        tasks = []

        for f in factories:
            if not f.active:
                continue

            reman_tasks = []
            prod_tasks  = []

            for tid, tech in f.technologies.items():
                # Use baseline as the starting reference quantity
                base_qty = baseline_prod_plan.get((f.name, tid), 0.0)
                # Default to 80% of capacity when not in plan
                if base_qty <= 0:
                    base_qty = tech["capacity"] * 0.8

                if tech["type"] == "remanufacturing":
                    # Apply remanufacturing boost (capped at full capacity)
                    qty = min(base_qty * self.remanufacturing_boost, tech["capacity"])
                    reman_tasks.append((f.name, tid, qty))
                else:
                    prod_tasks.append((f.name, tid, base_qty))

            if self.production_mode == "reman_first":
                tasks.extend(reman_tasks)
                tasks.extend(prod_tasks)
            elif self.production_mode == "production_first":
                tasks.extend(prod_tasks)
                tasks.extend(reman_tasks)
            elif self.production_mode == "conserve":
                # FIX: conserve reduces ALL production to 50% — this is the
                # REPLACEMENT quantity, not 50% on top of normal
                for (fn, tid, qty) in (prod_tasks + reman_tasks):
                    tasks.append((fn, tid, qty * 0.5))
            else:
                # baseline — same quantities as normal but may reorder
                tasks.extend(prod_tasks)
                tasks.extend(reman_tasks)

        return tasks

    def __repr__(self):
        return (f"RecoveryStrategy({self.name}, "
                f"mode={self.production_mode}, "
                f"transport={self.transport_mode})")


# =============================================================================
# STRATEGY DEFINITIONS BY DISRUPTION TYPE
# =============================================================================

STRATEGIES_BY_DISRUPTION = {

    # -------------------------------------------------------------------------
    # SUPPLIER FAILURE — raw material supply cut off for several periods
    # -------------------------------------------------------------------------
    "supplier_failure": [
        RecoveryStrategy(
            name="A — Maximise Remanufacturing",
            production_mode="reman_first",
            market_priority="proportional",
            transport_mode="truck",
            remanufacturing_boost=1.5,
            safety_stock_draw=False,
        ),
        RecoveryStrategy(
            name="B — Prioritise Virgin Production",
            production_mode="production_first",
            market_priority="proportional",
            transport_mode="truck",
            remanufacturing_boost=1.0,
            safety_stock_draw=True,
        ),
        RecoveryStrategy(
            name="C — Ration by Market Priority",
            production_mode="baseline",
            market_priority="demand_ranked",
            transport_mode="truck",
            remanufacturing_boost=1.0,
            safety_stock_draw=False,
        ),
    ],

    # -------------------------------------------------------------------------
    # FACTORY DOWNTIME — one factory offline for several periods
    # -------------------------------------------------------------------------
    "factory_downtime": [
        RecoveryStrategy(
            name="A — Emergency Air Freight",
            production_mode="production_first",
            market_priority="demand_ranked",
            transport_mode="air",
            remanufacturing_boost=1.0,
            safety_stock_draw=True,
        ),
        RecoveryStrategy(
            name="B — Remanufacturing Substitute",
            production_mode="reman_first",
            market_priority="proportional",
            transport_mode="truck",
            remanufacturing_boost=1.5,
            safety_stock_draw=False,
        ),
        RecoveryStrategy(
            name="C — Conserve and Ration",
            production_mode="conserve",
            market_priority="demand_ranked",
            transport_mode="sea",
            remanufacturing_boost=1.0,
            safety_stock_draw=False,
        ),
    ],

    # -------------------------------------------------------------------------
    # DEMAND SPIKE — market demand increases 50% for several periods
    # -------------------------------------------------------------------------
    "demand_spike": [
        RecoveryStrategy(
            name="A — Air Freight Scale-up",
            production_mode="production_first",
            market_priority="demand_ranked",
            transport_mode="air",
            remanufacturing_boost=1.0,
            safety_stock_draw=True,
        ),
        RecoveryStrategy(
            name="B — Sea Freight Buffer",
            production_mode="production_first",
            market_priority="proportional",
            transport_mode="sea",
            remanufacturing_boost=1.0,
            safety_stock_draw=False,
        ),
        RecoveryStrategy(
            name="C — Remanufacture to Fill Gap",
            production_mode="reman_first",
            market_priority="demand_ranked",
            transport_mode="truck",
            remanufacturing_boost=1.5,
            safety_stock_draw=False,
        ),
    ],

    # -------------------------------------------------------------------------
    # RETURN RATE DROP — product returns fall 60%, cutting remanufacturing inputs
    #
    # FIX: Previously A and C were identical (both production_first, truck,
    # proportional). Now C uses sea transport + safety_stock_draw to create
    # a genuine cost/emissions/service-level trade-off in the TBL table.
    # -------------------------------------------------------------------------
    "return_rate_drop": [
        RecoveryStrategy(
            name="A — Shift to Virgin Production",
            production_mode="production_first",
            market_priority="proportional",
            transport_mode="truck",
            remanufacturing_boost=1.0,
            safety_stock_draw=False,
        ),
        RecoveryStrategy(
            name="B — Conserve Raw Materials",
            production_mode="conserve",
            market_priority="demand_ranked",
            transport_mode="truck",
            remanufacturing_boost=1.0,
            safety_stock_draw=False,
        ),
        RecoveryStrategy(
            # FIX: was identical to A. Now: sea freight reduces transport cost/
            # emissions; safety_stock_draw maintains service level at the cost
            # of drawing down warehouse buffer — a distinct TBL profile.
            name="C — Sea Freight + Safety Stock",
            production_mode="production_first",
            market_priority="proportional",
            transport_mode="sea",
            remanufacturing_boost=1.0,
            safety_stock_draw=True,
        ),
    ],

    # -------------------------------------------------------------------------
    # WAREHOUSE DISRUPTION
    # Warehouse throughput is reduced — less stock reaches markets each period.
    # -------------------------------------------------------------------------
    "warehouse_disruption": [
        RecoveryStrategy(
            name="A — Demand Ranked Rationing",
            production_mode="baseline",
            market_priority="demand_ranked",
            transport_mode="truck",
            remanufacturing_boost=1.0,
            safety_stock_draw=False,
        ),
        RecoveryStrategy(
            name="B — Air Freight Priority Markets",
            production_mode="baseline",
            market_priority="demand_ranked",
            transport_mode="air",
            remanufacturing_boost=1.0,
            safety_stock_draw=True,
        ),
        RecoveryStrategy(
            name="C — Proportional + Safety Stock",
            production_mode="baseline",
            market_priority="proportional",
            transport_mode="truck",
            remanufacturing_boost=1.0,
            safety_stock_draw=True,
        ),
    ],

    # -------------------------------------------------------------------------
    # PORT CLOSURE
    # Port_Hamburg is closed — Vancouver shipments must reroute or be deferred.
    # -------------------------------------------------------------------------
    "port_closure": [
        RecoveryStrategy(
            name="A — Reroute via Barcelona (Sea)",
            production_mode="baseline",
            market_priority="proportional",
            transport_mode="sea",
            remanufacturing_boost=1.0,
            safety_stock_draw=False,
        ),
        RecoveryStrategy(
            name="B — Emergency Air Freight",
            production_mode="baseline",
            market_priority="demand_ranked",
            transport_mode="air",
            remanufacturing_boost=1.0,
            safety_stock_draw=True,
        ),
        RecoveryStrategy(
            name="C — Accept Vancouver Unmet",
            production_mode="baseline",
            market_priority="demand_ranked",
            transport_mode="truck",
            remanufacturing_boost=1.0,
            safety_stock_draw=False,
        ),
    ],
}


# Map disruption scenario names to dictionary keys
DISRUPTION_KEY_MAP = {
    "Supplier Failure":     "supplier_failure",
    "Factory Downtime":     "factory_downtime",
    "Demand Spike":         "demand_spike",
    "Return Rate Drop":     "return_rate_drop",
    "Warehouse Disruption": "warehouse_disruption",
    "Port Closure":         "port_closure",
}


def get_disruption_key(scenario_name):
    """Return the strategy dictionary key for a given scenario name."""
    for key, val in DISRUPTION_KEY_MAP.items():
        if key.lower() in scenario_name.lower():
            return val
    return None
