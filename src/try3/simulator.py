"""
simulator.py — Digital Twin Closed-Loop Supply Chain Simulator

FIXES applied in this version
==============================
1. Strategy logic REPLACES baseline flows during disruption windows.
   Previously, `prod_tasks` from strategy.get_production_tasks() was
   executed AND THEN the baseline plan ran again in normal operation —
   effectively doubling production and masking the disruption impact.
   Now, during disruption periods the simulator runs ONLY the strategy
   tasks; the baseline plan is not touched.

2. SupplierNode.active flag (nodes.py fix) means a disrupted supplier
   ships 0 units regardless of inventory. Previously disrupt() only
   zeroed restock_rate, leaving the existing inventory buffer available —
   so "Supplier Failure" had almost no effect for many periods.

3. active_employees now reflects conserve mode: a factory running at
   50% capacity is credited with 50% of its employee count, creating a
   genuine social cost for that strategy.

4. safety_stock_draw: when True, the warehouse ships up to 150% of
   normal per-market allocation (draws down safety buffer). When False
   and stock is tight, the warehouse respects normal allocation limits.
"""

import random
import pandas as pd

from .constants import (
    RAW_MATERIALS, FINAL_PRODUCTS, RECOVERED_PRODUCTS,
    TRUCK_COST_PER_UNIT_PER_KM, AIR_COST_PER_KM, SEA_HANDLING_COST_PER_UNIT,
    TRANSPORT_EMISSIONS_PER_KM, PRODUCT_WEIGHT,
    MARKET_DEMAND_PER_PERIOD, DEMAND_STD_FACTOR, RETURN_RATES,
    HOLDING_COST, DISTANCE_TABLE, PRODUCTION_COST, PRODUCTION_EMISSIONS,
)
from .nodes import SupplierNode, FactoryNode, WarehouseNode, MarketNode

# =============================================================================
# ROUTING DICTIONARIES — network topology (Case F)
# =============================================================================

SUPPLIER_FACTORY_ROUTING = {
    "Supplier_Lyon":   ["Factory_Lyon"],
    "Supplier_Bremen": ["Factory_Lyon", "Factory_Bremen"],
    "Supplier_Galway": ["Factory_Galway"],
}

FACTORY_WAREHOUSE_ROUTING = {
    "Factory_Lyon":   ["Warehouse_Lyon"],
    "Factory_Bremen": ["Warehouse_Lyon"],
    "Factory_Galway": [],   # ships direct to Market_Galway only
}

WAREHOUSE_MARKET_ROUTING = {
    "Warehouse_Lyon": [
        "Market_Lyon",
        "Market_Bremen",
        "Market_Lisbon",
        "Market_Madrid",
        "Market_Vancouver",   # via sea through Port_Hamburg
    ],
}

FACTORY_DIRECT_MARKET = {
    "Factory_Galway": "Market_Galway",
}

ARC_TRANSPORT_MODE = {
    ("Supplier_Lyon",    "Factory_Lyon"):    "truck",
    ("Supplier_Bremen",  "Factory_Lyon"):    "truck",
    ("Supplier_Bremen",  "Factory_Bremen"):  "truck",
    ("Supplier_Galway",  "Factory_Galway"):  "truck",
    ("Factory_Lyon",     "Warehouse_Lyon"):  "truck",
    ("Factory_Bremen",   "Warehouse_Lyon"):  "truck",
    ("Warehouse_Lyon",   "Port_Hamburg"):    "truck",
    ("Warehouse_Lyon",   "Port_Barcelona"):  "truck",
    ("Port_Hamburg",     "Port_Vancouver"):  "sea",
    ("Port_Barcelona",   "Port_Vancouver"):  "sea",
    ("Port_Vancouver",   "Market_Vancouver"): "truck",
    ("Warehouse_Lyon",   "Market_Lyon"):     "truck",
    ("Warehouse_Lyon",   "Market_Bremen"):   "truck",
    ("Warehouse_Lyon",   "Market_Lisbon"):   "truck",
    ("Warehouse_Lyon",   "Market_Madrid"):   "truck",
    ("Factory_Galway",   "Market_Galway"):   "truck",
}

# Only these arcs switch sea → air when strategy.transport_mode == "air"
SWITCHABLE_ARCS = [
    ("Port_Hamburg",   "Port_Vancouver"),
    ("Port_Barcelona", "Port_Vancouver"),
]


class ClosedLoopSimulator:
    """
    Period-by-period Digital Twin simulation of a closed-loop supply chain.
    """

    def __init__(self, periods=48, scenario=None, strategy=None, run_label=None):
        self.periods             = periods
        self.scenario            = scenario or {}
        self.strategy            = strategy
        self.run_label           = run_label
        self.port_hamburg_closed = False
        self._build_nodes()
        self._run_baseline()
        self.records = []

    # =========================================================================
    # NODE CONSTRUCTION
    # =========================================================================

    def _build_nodes(self):

        self.suppliers = [
            SupplierNode("Supplier_Lyon",
                inventory={"rm1": 5_000_000, "rm2": 5_000_000,
                           "rm3": 6_000_000, "rm4": 1_000_000},
                capacity={"rm1": 5_400_000, "rm2": 5_400_000,
                          "rm3": 6_000_000, "rm4": 1_000_000},
                restock_rate={"rm1": 450_000, "rm2": 450_000,
                              "rm3": 500_000, "rm4": 83_333},
                region="Lyon"),

            SupplierNode("Supplier_Bremen",
                inventory={"rm1": 4_800_000, "rm2": 4_800_000,
                           "rm3": 6_500_000, "rm4": 1_600_000},
                capacity={"rm1": 5_225_000, "rm2": 5_225_000,
                          "rm3": 6_875_000, "rm4": 1_650_000},
                restock_rate={"rm1": 435_000, "rm2": 435_000,
                              "rm3": 572_000, "rm4": 137_500},
                region="Bremen"),

            SupplierNode("Supplier_Galway",
                inventory={"rm1": 4_300_000, "rm2": 4_300_000,
                           "rm3": 6_100_000, "rm4":   950_000},
                capacity={"rm1": 4_655_000, "rm2": 4_655_000,
                          "rm3": 6_370_000, "rm4":   980_000},
                restock_rate={"rm1": 387_000, "rm2": 387_000,
                              "rm3": 530_000, "rm4":  81_666},
                region="Galway"),
        ]

        self.factories = [
            FactoryNode("Factory_Lyon",
                rm_inventory={"rm1": 80_000, "rm2": 60_000,
                              "rm3": 50_000, "rm4": 15_000},
                fp_inventory={"fp1": 0, "fp2": 0, "fp3": 0},
                rm_capacity={"rm1": 2_000_000, "rm2": 1_800_000,
                             "rm3": 1_500_000, "rm4":   500_000},
                fp_capacity={"fp1": 1_000_000, "fp2": 800_000, "fp3": 700_000},
                technology_ids=["pr1", "pr3", "pr4", "re1", "re2", "re3"],
                employees=15,
                region="Lyon"),

            FactoryNode("Factory_Bremen",
                rm_inventory={"rm1": 70_000, "rm2": 80_000,
                              "rm3": 60_000, "rm4": 20_000},
                fp_inventory={"fp1": 0, "fp2": 0, "fp3": 0},
                rm_capacity={"rm1": 1_800_000, "rm2": 1_600_000,
                             "rm3": 1_400_000, "rm4":   450_000},
                fp_capacity={"fp1": 900_000, "fp2": 700_000, "fp3": 600_000},
                # FIX: Bremen has NO remanufacturing (no fp3 via pr3)
                technology_ids=["pr1", "pr2", "pr4"],
                employees=22,
                region="Bremen"),

            FactoryNode("Factory_Galway",
                rm_inventory={"rm1": 300_000, "rm2": 250_000,
                              "rm3": 200_000, "rm4":  60_000},
                fp_inventory={"fp1": 0, "fp2": 0, "fp3": 0},
                rm_capacity={"rm1": 1_500_000, "rm2": 1_400_000,
                             "rm3": 1_200_000, "rm4":   400_000},
                fp_capacity={"fp1": 800_000, "fp2": 600_000, "fp3": 500_000},
                technology_ids=["pr1", "pr2", "pr3", "re1", "re2", "re3"],
                employees=277,
                region="Galway"),
        ]

        self.warehouses = [
            WarehouseNode("Warehouse_Lyon",
                # FIX: reduced from 382k (1.0 period buffer) to ~0.5 period buffer
                # so supplier/factory disruptions degrade service level visibly.
                inventory={"fp1": 27_000, "fp2": 16_000, "fp3": 18_000},
                capacity={"fp1": 2_000_000, "fp2": 1_500_000, "fp3": 1_200_000},
                employees=0,
                region="Lyon"),
        ]

        self.markets = [
            MarketNode("Market_Lyon",
                base_demand={fp: MARKET_DEMAND_PER_PERIOD["Market_Lyon"][fp]
                             for fp in FINAL_PRODUCTS},
                demand_std={fp: MARKET_DEMAND_PER_PERIOD["Market_Lyon"][fp] * DEMAND_STD_FACTOR
                            for fp in FINAL_PRODUCTS},
                return_rate=RETURN_RATES.copy(),
                region="Lyon"),

            MarketNode("Market_Bremen",
                base_demand={fp: MARKET_DEMAND_PER_PERIOD["Market_Bremen"][fp]
                             for fp in FINAL_PRODUCTS},
                demand_std={fp: MARKET_DEMAND_PER_PERIOD["Market_Bremen"][fp] * DEMAND_STD_FACTOR
                            for fp in FINAL_PRODUCTS},
                return_rate=RETURN_RATES.copy(),
                region="Bremen"),

            MarketNode("Market_Vancouver",
                base_demand={fp: MARKET_DEMAND_PER_PERIOD["Market_Vancouver"][fp]
                             for fp in FINAL_PRODUCTS},
                demand_std={fp: MARKET_DEMAND_PER_PERIOD["Market_Vancouver"][fp] * DEMAND_STD_FACTOR
                            for fp in FINAL_PRODUCTS},
                return_rate=RETURN_RATES.copy(),
                region="Vancouver"),

            MarketNode("Market_Galway",
                base_demand={fp: MARKET_DEMAND_PER_PERIOD["Market_Galway"][fp]
                             for fp in FINAL_PRODUCTS},
                demand_std={fp: MARKET_DEMAND_PER_PERIOD["Market_Galway"][fp] * DEMAND_STD_FACTOR
                            for fp in FINAL_PRODUCTS},
                return_rate=RETURN_RATES.copy(),
                region="Galway"),

            MarketNode("Market_Lisbon",
                base_demand={fp: MARKET_DEMAND_PER_PERIOD["Market_Lisbon"][fp]
                             for fp in FINAL_PRODUCTS},
                demand_std={fp: MARKET_DEMAND_PER_PERIOD["Market_Lisbon"][fp] * DEMAND_STD_FACTOR
                            for fp in FINAL_PRODUCTS},
                return_rate=RETURN_RATES.copy(),
                region="Lisbon"),

            MarketNode("Market_Madrid",
                base_demand={fp: MARKET_DEMAND_PER_PERIOD["Market_Madrid"][fp]
                             for fp in FINAL_PRODUCTS},
                demand_std={fp: MARKET_DEMAND_PER_PERIOD["Market_Madrid"][fp] * DEMAND_STD_FACTOR
                            for fp in FINAL_PRODUCTS},
                return_rate=RETURN_RATES.copy(),
                region="Madrid"),
        ]

    # =========================================================================
    # BASELINE PLAN
    # =========================================================================

    def _run_baseline(self):
        """
        Hardcoded baseline production plan from Camarneiro (2024) Case F.
        Reflects Case F technology assignments:
          - Factory_Bremen: pr1, pr2, pr4 only (no re*, no pr3)
          - Factory_Lyon / Factory_Galway: full technology set
        """
        # FIX: Baseline quantities calibrated to match demand (1.03-1.05x)
        # so disruptions create visible service degradation.
        # Previous values were ~1.3-1.5x demand — disruptions had no effect.
        #
        # Technology note (Case F):
        #   Lyon has no pr2 — fp2 only via re2 (rp2-limited)
        #   Bremen has no pr3, re*, so no fp3 and no remanufacturing
        #   Galway is self-contained island (direct to Market_Galway)
        self.baseline_prod_plan = {
            ("Factory_Lyon",   "pr1"):  80_000,   # fp1
            ("Factory_Lyon",   "pr3"):  55_000,   # fp3
            ("Factory_Lyon",   "re1"):   8_000,   # fp1 remanuf (rp1-limited)
            ("Factory_Lyon",   "re2"):   5_000,   # fp2 remanuf (rp2-limited)
            ("Factory_Lyon",   "re3"):   4_000,   # fp3 remanuf (rp3-limited)
            ("Factory_Bremen", "pr1"):  55_000,   # fp1
            ("Factory_Bremen", "pr2"):  65_000,   # fp2
            ("Factory_Galway", "pr1"):  22_000,   # fp1 for Market_Galway
            ("Factory_Galway", "pr2"):  28_000,   # fp2 for Market_Galway + small surplus
            ("Factory_Galway", "pr3"):  55_000,   # fp3 for Market_Galway + wh surplus
            ("Factory_Galway", "re1"):   4_000,
            ("Factory_Galway", "re2"):   3_000,
            ("Factory_Galway", "re3"):   3_000,
        }

    # =========================================================================
    # DISRUPTION MANAGEMENT
    # =========================================================================

    def _disruption_active(self, t):
        s = self.scenario
        if "supplier_failure" in s:
            entries = s["supplier_failure"]
            if isinstance(entries, dict):
                entries = [entries]
            for sf in entries:
                if sf["start"] <= t <= sf["end"]:
                    return True
        for key in ["factory_downtime", "demand_spike",
                    "return_rate_drop", "warehouse_disruption", "port_closure"]:
            if key in s and s[key]["start"] <= t <= s[key]["end"]:
                return True
        return False

    def _apply_disruption(self, t):
        s = self.scenario

        if "supplier_failure" in s:
            entries = s["supplier_failure"]
            if isinstance(entries, dict):
                entries = [entries]
            for sf in entries:
                for sup in self.suppliers:
                    if sup.name == sf["node"]:
                        if sf["start"] <= t <= sf["end"]:
                            sup.disrupt()
                        elif t == sf["end"] + 1:
                            sup.restore()

        if "factory_downtime" in s:
            fd = s["factory_downtime"]
            for fac in self.factories:
                if fac.name == fd["node"]:
                    if fd["start"] <= t <= fd["end"]:
                        fac.disrupt()
                    elif t == fd["end"] + 1:
                        fac.restore()

        if "demand_spike" in s:
            ds = s["demand_spike"]
            for m in self.markets:
                if ds["start"] <= t <= ds["end"]:
                    m.disrupt_demand(ds["multiplier"])
                elif t == ds["end"] + 1:
                    m.restore_demand()

        if "return_rate_drop" in s:
            rd = s["return_rate_drop"]
            for m in self.markets:
                if rd["start"] <= t <= rd["end"]:
                    m.disrupt_returns(rd["factor"])
                elif t == rd["end"] + 1:
                    m.restore_returns()

        if "warehouse_disruption" in s:
            wd = s["warehouse_disruption"]
            for wh in self.warehouses:
                if wh.name == wd["node"]:
                    if wd["start"] <= t <= wd["end"]:
                        wh.disrupt_throughput(wd["factor"])
                    elif t == wd["end"] + 1:
                        wh.restore_throughput()

        if "port_closure" in s:
            pc = s["port_closure"]
            if pc["node"] == "Port_Hamburg":
                if pc["start"] <= t <= pc["end"]:
                    self.port_hamburg_closed = True
                elif t == pc["end"] + 1:
                    self.port_hamburg_closed = False

    # =========================================================================
    # TRANSPORT HELPERS
    # =========================================================================

    def _arc_mode(self, src, dst):
        base = ARC_TRANSPORT_MODE.get((src, dst), "truck")
        if (self.strategy and (src, dst) in SWITCHABLE_ARCS
                and self.strategy.transport_mode == "air"):
            return "air"
        return base

    def _arc_cost_emissions(self, src, dst, qty, fp):
        if qty <= 0:
            return 0.0, 0.0
        mode = self._arc_mode(src, dst)
        try:
            dist = DISTANCE_TABLE.loc[src, dst]
        except KeyError:
            dist = 0
        weight = PRODUCT_WEIGHT.get(fp, 0.5)
        if mode == "air":
            cost = qty * weight * dist * AIR_COST_PER_KM
        elif mode == "sea":
            cost = qty * SEA_HANDLING_COST_PER_UNIT
        else:
            cost = qty * dist * TRUCK_COST_PER_UNIT_PER_KM
        emissions = (qty * weight * dist
                     * TRANSPORT_EMISSIONS_PER_KM.get(mode, TRANSPORT_EMISSIONS_PER_KM["truck"]))
        return cost, emissions

    def _wh_market_cost_emissions(self, wh_name, mkt_name, qty, fp):
        if qty <= 0:
            return 0.0, 0.0
        if mkt_name == "Market_Vancouver":
            if self.port_hamburg_closed and self.strategy:
                # Strategy active: reroute via Port_Barcelona
                transit_port = "Port_Barcelona"
            elif self.port_hamburg_closed:
                # No Recovery: Vancouver is unserved — caller must pass qty=0
                return 0.0, 0.0
            else:
                transit_port = "Port_Hamburg"
            legs = [
                (wh_name,      transit_port),
                (transit_port, "Port_Vancouver"),
                ("Port_Vancouver", mkt_name),
            ]
            total_cost, total_ems = 0.0, 0.0
            for (s, d) in legs:
                c, e = self._arc_cost_emissions(s, d, qty, fp)
                total_cost += c
                total_ems  += e
            return total_cost, total_ems
        return self._arc_cost_emissions(wh_name, mkt_name, qty, fp)

    # =========================================================================
    # PERIOD SIMULATION
    # =========================================================================

    def simulate_period(self, t):
        data = {"period": t}
        self._apply_disruption(t)

        disruption_on = self._disruption_active(t)
        data["transport_mode"] = (
            self.strategy.transport_mode if (self.strategy and disruption_on) else "truck"
        )

        # --- STEP 1: Supplier restock ---
        for s in self.suppliers:
            s.restock()

        # --- STEP 2: Suppliers ship to factories ---
        # FIX: disrupted suppliers return 0 from ship() due to active=False flag
        total_rm_shipped = {rm: 0.0 for rm in RAW_MATERIALS}
        for factory in self.factories:
            if not factory.active:
                continue
            for supplier in self.suppliers:
                if factory.name not in SUPPLIER_FACTORY_ROUTING.get(supplier.name, []):
                    continue
                for rm_type in factory.rm_capacity:
                    if rm_type not in supplier.inventory:
                        continue
                    space    = factory.rm_capacity[rm_type] - factory.rm_inventory.get(rm_type, 0)
                    needed   = max(0.0, space * 0.8)
                    n_sup    = sum(1 for s in self.suppliers
                                   if factory.name in SUPPLIER_FACTORY_ROUTING.get(s.name, []))
                    delivered = supplier.ship(rm_type, needed / max(n_sup, 1))
                    factory.receive_rm(rm_type, delivered)
                    total_rm_shipped[rm_type] += delivered

        for rm, val in total_rm_shipped.items():
            data[f"rm_shipped_{rm}"] = round(val, 2)

        # --- STEP 3: Production & remanufacturing ---
        # FIX: during disruption, strategy tasks REPLACE the baseline.
        # We do NOT run both. Outside disruption, always use baseline.
        if self.strategy and disruption_on:
            # Strategy tasks are the complete replacement production plan
            prod_tasks = self.strategy.get_production_tasks(
                self.factories, self.baseline_prod_plan
            )
        else:
            prod_tasks = [(fname, tid, qty)
                          for (fname, tid), qty in self.baseline_prod_plan.items()]

        total_produced       = {fp: 0.0 for fp in FINAL_PRODUCTS}
        total_remanufactured = {fp: 0.0 for fp in FINAL_PRODUCTS}
        total_prod_cost      = 0.0
        total_prod_emissions = 0.0

        # FIX: track what fraction of capacity is used per factory for employee calc
        factory_utilisation = {f.name: 0.0 for f in self.factories}
        factory_capacity    = {f.name: sum(
            tech["capacity"] for tech in f.technologies.values()
        ) for f in self.factories}

        for (fname, tid, qty) in prod_tasks:
            factory = next((f for f in self.factories if f.name == fname), None)
            if not factory:
                continue
            actual = factory.produce(tid, qty)
            if actual > 0 and tid in factory.technologies:
                tech = factory.technologies[tid]
                total_prod_cost      += actual * PRODUCTION_COST.get(tid, 0)
                total_prod_emissions += actual * PRODUCTION_EMISSIONS.get(tid, 0)
                factory_utilisation[fname] += actual
                if tech["type"] == "production":
                    total_produced[tech["output"]] += actual
                else:
                    total_remanufactured[tech["output"]] += actual

        for fp in FINAL_PRODUCTS:
            data[f"produced_{fp}"]       = round(total_produced[fp], 2)
            data[f"remanufactured_{fp}"] = round(total_remanufactured[fp], 2)

        # --- STEP 4: Factories ship to warehouses ---
        total_transport_cost      = 0.0
        total_transport_emissions = 0.0
        total_f_to_w = {fp: 0.0 for fp in FINAL_PRODUCTS}

        market_demand   = {m.name: m.generate_demand() for m in self.markets}
        market_received = {m.name: {fp: 0.0 for fp in FINAL_PRODUCTS} for m in self.markets}

        for factory in self.factories:
            if not factory.active:
                continue
            target_wh_names = FACTORY_WAREHOUSE_ROUTING.get(factory.name, [])
            if not target_wh_names:
                continue
            for fp in FINAL_PRODUCTS:
                available = factory.fp_inventory.get(fp, 0)
                if available <= 0:
                    continue
                per_wh = available / max(len(target_wh_names), 1)
                for wh_name in target_wh_names:
                    wh = next((w for w in self.warehouses if w.name == wh_name), None)
                    if wh:
                        shipped = factory.ship_fp(fp, per_wh)
                        wh.receive(fp, shipped)
                        total_f_to_w[fp] += shipped
                        c, e = self._arc_cost_emissions(factory.name, wh_name, shipped, fp)
                        total_transport_cost      += c
                        total_transport_emissions += e

        for fp, val in total_f_to_w.items():
            data[f"factory_to_wh_{fp}"] = round(val, 2)

        # Galway direct flow (self-contained island — bypasses warehouse)
        galway_factory = next((f for f in self.factories if f.name == "Factory_Galway"), None)
        if galway_factory and galway_factory.active:
            for fp in FINAL_PRODUCTS:
                available  = galway_factory.fp_inventory.get(fp, 0)
                demand_qty = market_demand.get("Market_Galway", {}).get(fp, 0)
                shipped    = galway_factory.ship_fp(fp, min(available, demand_qty))
                market_received["Market_Galway"][fp] = shipped
                c, e = self._arc_cost_emissions("Factory_Galway", "Market_Galway", shipped, fp)
                total_transport_cost      += c
                total_transport_emissions += e

        # --- STEP 5: Warehouses ship to markets ---
        total_demand  = {fp: 0.0 for fp in FINAL_PRODUCTS}
        total_shipped = {fp: 0.0 for fp in FINAL_PRODUCTS}
        total_unmet   = {fp: 0.0 for fp in FINAL_PRODUCTS}

        for wh in self.warehouses:
            target_markets = list(WAREHOUSE_MARKET_ROUTING.get(wh.name, []))

            if (self.strategy and disruption_on
                    and self.strategy.market_priority == "demand_ranked"):
                target_markets = sorted(
                    target_markets,
                    key=lambda mn: sum(market_demand.get(mn, {}).values()),
                    reverse=True,
                )

            for mkt_name in target_markets:
                market = next((m for m in self.markets if m.name == mkt_name), None)
                if not market:
                    continue
                for fp in FINAL_PRODUCTS:
                    needed = market_demand.get(mkt_name, {}).get(fp, 0)

                    # FIX: safety_stock_draw allows shipping up to 150% of demand
                    # from warehouse buffer — models drawing down safety stock.
                    # Without it, only ship what's been demanded (no extra draw).
                    if (self.strategy and disruption_on
                            and self.strategy.safety_stock_draw):
                        ship_qty = needed * 1.5  # draw safety stock
                    else:
                        ship_qty = needed

                    # No Recovery: Vancouver blocked entirely when port is closed
                    if (mkt_name == "Market_Vancouver"
                            and self.port_hamburg_closed
                            and not (self.strategy and disruption_on)):
                        ship_qty = 0

                    shipped = wh.ship(fp, ship_qty)
                    market_received[mkt_name][fp] = (
                        market_received[mkt_name].get(fp, 0) + shipped
                    )
                    c, e = self._wh_market_cost_emissions(wh.name, mkt_name, shipped, fp)
                    total_transport_cost      += c
                    total_transport_emissions += e

        # Tally demand, shipped, unmet across all markets
        for m in self.markets:
            demand = market_demand[m.name]
            for fp in FINAL_PRODUCTS:
                total_demand[fp]  += demand[fp]
                recv               = market_received[m.name].get(fp, 0.0)
                total_shipped[fp] += recv
                total_unmet[fp]   += max(0.0, demand[fp] - recv)

        for fp in FINAL_PRODUCTS:
            data[f"demand_{fp}"]  = round(total_demand[fp],  2)
            data[f"shipped_{fp}"] = round(total_shipped[fp], 2)
            data[f"unmet_{fp}"]   = round(total_unmet[fp],   2)

        # --- STEP 6: Returns → factories ---
        total_returns = {rp: 0.0 for rp in RECOVERED_PRODUCTS}
        lyon_factory  = next((f for f in self.factories if f.name == "Factory_Lyon"), None)

        for market in self.markets:
            returns = market.generate_returns(market_received.get(market.name, {}))
            target_f = galway_factory if market.name == "Market_Galway" else lyon_factory
            for rp, qty in returns.items():
                total_returns[rp] += qty
                if target_f:
                    target_f.receive_rp(rp, qty)

        for rp, val in total_returns.items():
            data[f"returns_{rp}"] = round(val, 2)

        # --- STEP 7: TBL metrics ---
        holding_cost = sum(
            w.inventory.get(fp, 0) * HOLDING_COST.get(fp, 0.015)
            for w in self.warehouses
            for fp in FINAL_PRODUCTS
        )
        data["total_cost"] = round(
            total_prod_cost + total_transport_cost + holding_cost, 2
        )
        data["total_emissions"] = round(
            total_prod_emissions + total_transport_emissions, 4
        )

        total_d = sum(total_demand.values())
        total_s = sum(total_shipped.values())
        data["service_level"] = round(
            (total_s / total_d * 100) if total_d > 0 else 100.0, 2
        )
        data["total_unmet"] = round(sum(total_unmet.values()), 2)

        # FIX: active_employees reflects utilisation under strategy.
        # A factory running conserve mode (50% of baseline quantities) is
        # credited with 50% of its employees — not the full headcount.
        # This gives strategy C (conserve) a genuine social cost.
        active_employees = 0.0
        for f in self.factories:
            if not f.active:
                continue  # offline factory = 0 employees contributing
            cap = factory_capacity.get(f.name, 1)
            util = factory_utilisation.get(f.name, 0.0)
            util_fraction = min(1.0, util / cap) if cap > 0 else 1.0
            if self.strategy and disruption_on and self.strategy.production_mode == "conserve":
                active_employees += f.employees * util_fraction
            else:
                active_employees += f.employees
        active_employees += sum(w.employees for w in self.warehouses)
        data["active_employees"] = round(active_employees, 1)

        data["supplier_inv"]  = round(sum(sum(s.inventory.values())    for s in self.suppliers), 2)
        data["factory_rm"]    = round(sum(sum(f.rm_inventory.values())  for f in self.factories), 2)
        data["factory_fp"]    = round(sum(sum(f.fp_inventory.values())  for f in self.factories), 2)
        data["factory_rp"]    = round(sum(sum(f.rp_inventory.values())  for f in self.factories), 2)
        data["warehouse_inv"] = round(sum(sum(w.inventory.values())     for w in self.warehouses), 2)

        data["disruption_active"] = disruption_on
        if self.run_label:
            data["strategy"] = self.run_label
        else:
            data["strategy"] = self.strategy.name if self.strategy else "No Recovery"

        self.records.append(data)
        return data

    # =========================================================================
    # RUN
    # =========================================================================

    def run(self):
        scenario_name = self.scenario.get("name", "Baseline")
        strategy_name = (
            self.run_label if self.run_label
            else (self.strategy.name if self.strategy else "No Recovery")
        )
        print(f"  Running: {scenario_name} | {strategy_name}")

        for t in range(1, self.periods + 1):
            self.simulate_period(t)

        return pd.DataFrame(self.records)


# =============================================================================
# SCENARIO DEFINITIONS
# =============================================================================

def get_scenarios():
    return [
        {"name": "Baseline"},

        {"name": "Dual Supplier Failure — Lyon + Bremen (periods 10-15)",
         "supplier_failure": [
             {"node": "Supplier_Lyon",   "start": 10, "end": 15},
             {"node": "Supplier_Bremen", "start": 10, "end": 15},
         ]},

        {"name": "Factory Downtime — Factory_Bremen (periods 8-14)",
         "factory_downtime": {
             "node": "Factory_Bremen",
             "start": 8, "end": 14,
         }},

        {"name": "Warehouse Disruption — 50% throughput (periods 9-15)",
         "warehouse_disruption": {
             "node": "Warehouse_Lyon",
             "factor": 0.5,
             "start": 9, "end": 15,
         }},

        {"name": "Port Closure — Port_Hamburg (periods 12-20)",
         "port_closure": {
             "node": "Port_Hamburg",
             "start": 12, "end": 20,
         }},

        {"name": "Demand Spike +50% (periods 12-18)",
         "demand_spike": {
             "start": 12, "end": 18,
             "multiplier": 1.5,
         }},
    ]
