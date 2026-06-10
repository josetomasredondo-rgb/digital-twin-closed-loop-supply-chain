import random
import pandas as pd
from .constants import (
    RAW_MATERIALS, FINAL_PRODUCTS, RECOVERED_PRODUCTS,
    PRODUCTION_COST, PRODUCTION_EMISSIONS,
    TRANSPORT_COST_PER_KM, TRANSPORT_EMISSIONS_PER_KM,
    TRANSPORT_MODE_MULTIPLIERS, HOLDING_COST, SOCIAL_DATA,
    DISTANCE_TABLE,
)
from .nodes import SupplierNode, FactoryNode, WarehouseNode, MarketNode
from .optimizer import SupplyChainOptimizer


class ClosedLoopSimulator:
    """
    Period flow each step:
      1. Apply disruption state changes
      2. Restock suppliers
      3. Ship RM from suppliers to factories (proportional by availability)
      4. Generate stochastic demand samples
      5. Decide production tasks (LP baseline plan or strategy override)
      6. Execute production
      7. Ship FP from factories to warehouses (greedy: fill spare capacity)
      8. Ship FP from warehouses to markets (proportional or demand-ranked)
      9. Process customer returns → rp routed back to factories
     10. Compute TBL metrics from executed quantities
    """

    def __init__(self, periods=24, scenario=None, strategy=None):
        self.periods   = periods
        self.scenario  = scenario or {}
        self.strategy  = strategy
        self.optimizer = SupplyChainOptimizer()
        self._build_nodes()
        self._run_baseline()
        self.records = []

    # ------------------------------------------------------------------
    # Node construction
    # ------------------------------------------------------------------

    def _build_nodes(self):
        self.suppliers = [
            SupplierNode("Supplier_A",
                inventory    = {"rm1": 150, "rm2": 120},
                capacity     = {"rm1": 250, "rm2": 220},
                restock_rate = {"rm1": 100, "rm2":  90}),
            SupplierNode("Supplier_B",
                inventory    = {"rm3": 100, "rm4": 80},
                capacity     = {"rm3": 200, "rm4": 180},
                restock_rate = {"rm3":  80, "rm4": 70}),
            SupplierNode("Supplier_C",
                inventory    = {"rm1": 80, "rm2": 60, "rm3": 50, "rm4": 40},
                capacity     = {"rm1": 180, "rm2": 160, "rm3": 140, "rm4": 130},
                restock_rate = {"rm1":  70, "rm2":  60, "rm3":  55, "rm4": 50}),
        ]

        self.factories = [
            FactoryNode("Factory_1",
                rm_inventory  = {"rm1": 80, "rm2": 60, "rm3": 30, "rm4": 40},
                fp_inventory  = {"fp1": 30, "fp2":  0, "fp3": 10},
                rm_capacity   = {"rm1": 200, "rm2": 180, "rm3": 150, "rm4": 170},
                fp_capacity   = {"fp1": 150, "fp2": 130, "fp3": 120},
                technology_ids= ["pr1", "pr4_fp1", "pr4_fp2", "pr3", "re1", "re2", "re3"],
                employees=15, region="Lyon"),
            FactoryNode("Factory_2",
                rm_inventory  = {"rm1": 60, "rm2": 70, "rm3": 40, "rm4": 50},
                fp_inventory  = {"fp1":  0, "fp2": 25, "fp3":  0},
                rm_capacity   = {"rm1": 180, "rm2": 200, "rm3": 160, "rm4": 180},
                fp_capacity   = {"fp1": 130, "fp2": 140, "fp3": 110},
                technology_ids= ["pr1", "pr2", "pr4_fp1", "pr4_fp2", "re1", "re2", "re3"],
                employees=22, region="Bremen"),
            FactoryNode("Factory_3",
                rm_inventory  = {"rm1": 50, "rm2": 50, "rm3": 35, "rm4": 35},
                fp_inventory  = {"fp1": 20, "fp2": 15, "fp3": 10},
                rm_capacity   = {"rm1": 170, "rm2": 170, "rm3": 140, "rm4": 140},
                fp_capacity   = {"fp1": 140, "fp2": 120, "fp3": 100},
                technology_ids= ["pr1", "pr2", "pr3", "re1", "re2", "re3"],
                employees=30, region="Galway"),
        ]

        self.warehouses = [
            WarehouseNode("Warehouse_1",
                inventory={"fp1": 40, "fp2": 30, "fp3": 25},
                capacity ={"fp1": 150, "fp2": 150, "fp3": 140},
                employees=15, region="North"),
            WarehouseNode("Warehouse_2",
                inventory={"fp1": 35, "fp2": 25, "fp3": 20},
                capacity ={"fp1": 130, "fp2": 130, "fp3": 120},
                employees=12, region="Central"),
            WarehouseNode("Warehouse_3",
                inventory={"fp1": 30, "fp2": 20, "fp3": 15},
                capacity ={"fp1": 120, "fp2": 120, "fp3": 110},
                employees=10, region="South"),
            WarehouseNode("Warehouse_4",
                inventory={"fp1": 25, "fp2": 35, "fp3": 30},
                capacity ={"fp1": 140, "fp2": 140, "fp3": 130},
                employees=14, region="East"),
            WarehouseNode("Warehouse_5",
                inventory={"fp1": 28, "fp2": 22, "fp3": 18},
                capacity ={"fp1": 125, "fp2": 125, "fp3": 115},
                employees=11, region="West"),
        ]

        self.markets = [
            MarketNode("Market_1",
                base_demand={"fp1": 30, "fp2": 25, "fp3": 20},
                demand_std ={"fp1":  5, "fp2":  4, "fp3":  3},
                return_rate={"fp1": 0.10, "fp2": 0.20, "fp3": 0.15}),
            MarketNode("Market_2",
                base_demand={"fp1": 25, "fp2": 20, "fp3": 18},
                demand_std ={"fp1":  4, "fp2":  4, "fp3":  3},
                return_rate={"fp1": 0.10, "fp2": 0.20, "fp3": 0.15}),
            MarketNode("Market_3",
                base_demand={"fp1": 20, "fp2": 18, "fp3": 15},
                demand_std ={"fp1":  4, "fp2":  3, "fp3":  3},
                return_rate={"fp1": 0.10, "fp2": 0.20, "fp3": 0.15}),
            MarketNode("Market_4",
                base_demand={"fp1": 28, "fp2": 22, "fp3": 19},
                demand_std ={"fp1":  5, "fp2":  4, "fp3":  4},
                return_rate={"fp1": 0.10, "fp2": 0.20, "fp3": 0.15}),
            MarketNode("Market_5",
                base_demand={"fp1": 22, "fp2": 18, "fp3": 16},
                demand_std ={"fp1":  4, "fp2":  3, "fp3":  3},
                return_rate={"fp1": 0.10, "fp2": 0.20, "fp3": 0.15}),
            MarketNode("Market_6",
                base_demand={"fp1": 26, "fp2": 24, "fp3": 21},
                demand_std ={"fp1":  5, "fp2":  4, "fp3":  4},
                return_rate={"fp1": 0.10, "fp2": 0.20, "fp3": 0.15}),
        ]

    # ------------------------------------------------------------------
    # LP baseline — runs once on the clean initial state.
    # Only the production plan (tech mix) is retained; shipping is
    # re-derived heuristically each period from current inventory.
    # ------------------------------------------------------------------

    def _run_baseline(self):
        # Zero out fp inventories so the LP solves for the production mix
        # needed to meet demand from scratch — this gives the steady-state plan.
        saved_f_fp = [f.fp_inventory.copy() for f in self.factories]
        saved_w_inv = [w.inventory.copy() for w in self.warehouses]
        for f in self.factories:
            f.fp_inventory = {fp: 0.0 for fp in FINAL_PRODUCTS}
        for w in self.warehouses:
            w.inventory = {fp: 0.0 for fp in FINAL_PRODUCTS}

        prod_plan, _, _, _ = self.optimizer.optimize(
            self.factories, self.warehouses, self.markets, self.suppliers
        )
        self.baseline_prod_plan = prod_plan

        for f, saved in zip(self.factories, saved_f_fp):
            f.fp_inventory = saved
        for w, saved in zip(self.warehouses, saved_w_inv):
            w.inventory = saved

    # ------------------------------------------------------------------
    # Disruption helpers
    # ------------------------------------------------------------------

    def _disruption_active(self, t):
        s = self.scenario
        if "supplier_failure" in s:
            sf = s["supplier_failure"]
            if sf["start"] <= t <= sf["end"]:
                return True
        if "factory_downtime" in s:
            fd = s["factory_downtime"]
            if fd["start"] <= t <= fd["end"]:
                return True
        if "demand_spike" in s:
            ds = s["demand_spike"]
            if ds["start"] <= t <= ds["end"]:
                return True
        if "return_rate_drop" in s:
            rd = s["return_rate_drop"]
            if rd["start"] <= t <= rd["end"]:
                return True
        return False

    def _apply_disruption_state(self, t):
        s = self.scenario

        if "supplier_failure" in s:
            sf = s["supplier_failure"]
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
                    m.disrupt(demand_multiplier=ds["multiplier"])
                elif t == ds["end"] + 1:
                    m.restore()

        if "return_rate_drop" in s:
            rd = s["return_rate_drop"]
            for m in self.markets:
                if rd["start"] <= t <= rd["end"]:
                    m.disrupt(return_rate_factor=rd["factor"])
                elif t == rd["end"] + 1:
                    m.restore()

    # ------------------------------------------------------------------
    # Decision helpers
    # ------------------------------------------------------------------

    def _get_prod_tasks(self, t):
        """Return ordered list of ((factory_name, tech_id), qty) for this period."""
        use_strategy = (
            self.strategy is not None
            and self._disruption_active(t)
            and self.strategy.production_mode != "baseline"
        )
        if use_strategy:
            return self.strategy.order_production_tasks(
                self.factories, self.baseline_prod_plan
            )
        return list(self.baseline_prod_plan.items())

    def _get_transport_mode(self, t):
        if self.strategy is not None and self._disruption_active(t):
            return self.strategy.transport_mode
        return "truck"

    def _ship_fw_greedy(self):
        """
        For each active factory, push all available fp to warehouses,
        distributing proportionally to each warehouse's spare capacity.
        Returns {(fname, wname, fp): planned_qty}.
        """
        plan = {}
        for f in self.factories:
            for w in self.warehouses:
                for fp in FINAL_PRODUCTS:
                    plan[(f.name, w.name, fp)] = 0.0

            if not f.active:
                continue

            for fp in FINAL_PRODUCTS:
                available = f.fp_inventory.get(fp, 0.0)
                if available <= 0:
                    continue
                spare = {w.name: max(0.0, w.capacity.get(fp, 0) - w.inventory.get(fp, 0))
                         for w in self.warehouses}
                total_spare = sum(spare.values())
                for w in self.warehouses:
                    share = spare[w.name] / total_spare if total_spare > 0 \
                            else 1.0 / len(self.warehouses)
                    plan[(f.name, w.name, fp)] = available * share
        return plan

    def _ship_wm_proportional(self, demand_samples):
        """
        Distribute warehouse stock to each market up to its demand share.
        Each warehouse contributes its proportional share of each market's demand,
        capped so total shipped <= total demand (surplus stays in warehouse).
        """
        plan = {}
        for w in self.warehouses:
            for fp in FINAL_PRODUCTS:
                total_demand = sum(demand_samples[m.name].get(fp, 0) for m in self.markets)
                available    = w.inventory.get(fp, 0.0)
                # warehouse contributes min(available, total_demand) distributed by share
                to_ship = min(available, total_demand) if total_demand > 0 else 0.0
                for m in self.markets:
                    share = (demand_samples[m.name].get(fp, 0) / total_demand
                             if total_demand > 0 else 1.0 / len(self.markets))
                    plan[(w.name, m.name, fp)] = to_ship * share
        return plan

    def _ship_wm_demand_ranked(self, demand_samples):
        """Fill highest-demand markets first until stock is exhausted."""
        ranked = sorted(
            self.markets,
            key=lambda m: sum(demand_samples[m.name].get(fp, 0) for fp in FINAL_PRODUCTS),
            reverse=True,
        )
        plan = {(w.name, m.name, fp): 0.0
                for w in self.warehouses for m in self.markets for fp in FINAL_PRODUCTS}
        for w in self.warehouses:
            for fp in FINAL_PRODUCTS:
                remaining = w.inventory.get(fp, 0.0)
                for m in ranked:
                    need = demand_samples[m.name].get(fp, 0)
                    send = min(remaining, need)
                    plan[(w.name, m.name, fp)] = send
                    remaining -= send
                    if remaining <= 0:
                        break
        return plan

    # ------------------------------------------------------------------
    # TBL metric computation
    # ------------------------------------------------------------------

    def _compute_cost(self, prod_executed, ship_fw_executed, ship_wm_executed, mode):
        mult = TRANSPORT_MODE_MULTIPLIERS[mode]
        cost = 0.0
        for (_, tid), qty in prod_executed:
            cost += qty * PRODUCTION_COST.get(tid, 0.0)
        for (fname, wname, fp), qty in ship_fw_executed.items():
            dist  = DISTANCE_TABLE.loc[fname, wname]
            cost += qty * dist * TRANSPORT_COST_PER_KM * mult["cost"]
            cost += qty * HOLDING_COST["warehouse"]
        for (wname, mname, fp), qty in ship_wm_executed.items():
            dist  = DISTANCE_TABLE.loc[wname, mname]
            cost += qty * dist * TRANSPORT_COST_PER_KM * mult["cost"]
        return cost

    def _compute_emissions(self, prod_executed, ship_fw_executed, ship_wm_executed, mode):
        mult = TRANSPORT_MODE_MULTIPLIERS[mode]
        emi  = 0.0
        for (_, tid), qty in prod_executed:
            emi += qty * PRODUCTION_EMISSIONS.get(tid, 0.0)
        for (fname, wname, fp), qty in ship_fw_executed.items():
            dist = DISTANCE_TABLE.loc[fname, wname]
            emi += qty * dist * TRANSPORT_EMISSIONS_PER_KM * mult["emissions"]
        for (wname, mname, fp), qty in ship_wm_executed.items():
            dist = DISTANCE_TABLE.loc[wname, mname]
            emi += qty * dist * TRANSPORT_EMISSIONS_PER_KM * mult["emissions"]
        return emi

    @staticmethod
    def _compute_social(factories, warehouses):
        impact = 0.0
        for node in list(factories) + list(warehouses):
            sd = SOCIAL_DATA.get(getattr(node, "region", ""))
            if sd:
                impact += node.employees * sd["gdp_per_capita"] * sd["unemployment_rate"]
        return impact

    # ------------------------------------------------------------------
    # Main period simulation
    # ------------------------------------------------------------------

    def simulate_period(self, t):
        data = {"period": t}
        self._apply_disruption_state(t)

        # Step 1 — Restock suppliers
        for s in self.suppliers:
            s.restock()

        # Step 2 — Ship RM: proportional by supplier availability, fill to 80% cap
        total_rm_shipped = {rm: 0.0 for rm in RAW_MATERIALS}
        for rm_type in RAW_MATERIALS:
            eligible_factories = [f for f in self.factories
                                  if f.active and f.rm_capacity.get(rm_type, 0) > 0]
            eligible_suppliers = [s for s in self.suppliers if rm_type in s.inventory]
            if not eligible_factories or not eligible_suppliers:
                continue
            total_supply = sum(s.inventory.get(rm_type, 0) for s in eligible_suppliers)
            if total_supply == 0:
                continue
            supplier_shares = {s.name: s.inventory.get(rm_type, 0) / total_supply
                               for s in eligible_suppliers}
            for factory in eligible_factories:
                needed = max(0.0, factory.rm_capacity[rm_type] * 0.8
                             - factory.rm_inventory.get(rm_type, 0))
                if needed == 0:
                    continue
                for supplier in eligible_suppliers:
                    delivered = supplier.ship(rm_type, needed * supplier_shares[supplier.name])
                    factory.receive_rm(rm_type, delivered)
                    total_rm_shipped[rm_type] += delivered

        for rm, val in total_rm_shipped.items():
            data[f"rm_shipped_{rm}"] = round(val, 2)

        # Step 3 — Generate demand (needed to plan wm shipments later)
        demand_samples = {m.name: m.generate_demand() for m in self.markets}

        # Step 4 — Decide production tasks and transport mode
        transport_mode = self._get_transport_mode(t)
        prod_tasks     = self._get_prod_tasks(t)
        data["transport_mode"] = transport_mode

        # Step 5 — Execute production
        total_produced       = {fp: 0.0 for fp in FINAL_PRODUCTS}
        total_remanufactured = {fp: 0.0 for fp in FINAL_PRODUCTS}
        prod_executed = []
        for (fname, tid), qty in prod_tasks:
            factory = next((f for f in self.factories if f.name == fname), None)
            if factory is None or not factory.active:
                continue
            actual = factory.produce(tid, qty)
            if actual > 0:
                prod_executed.append(((fname, tid), actual))
            tech = factory.technologies[tid]
            if tech["type"] == "production":
                total_produced[tech["output"]] += actual
            else:
                total_remanufactured[tech["output"]] += actual

        for fp in FINAL_PRODUCTS:
            data[f"produced_{fp}"]       = round(total_produced[fp], 2)
            data[f"remanufactured_{fp}"] = round(total_remanufactured[fp], 2)

        # Step 6 — Ship FP: factories → warehouses (greedy, current fp_inventory)
        fw_plan = self._ship_fw_greedy()
        total_f_to_w  = {fp: 0.0 for fp in FINAL_PRODUCTS}
        ship_fw_executed = {}
        for (fname, wname, fp), qty in fw_plan.items():
            factory   = next((f for f in self.factories  if f.name == fname), None)
            warehouse = next((w for w in self.warehouses if w.name == wname), None)
            if factory is None or warehouse is None or not factory.active or qty <= 0:
                ship_fw_executed[(fname, wname, fp)] = 0.0
                continue
            delivered = factory.ship_fp(fp, qty)
            warehouse.receive(fp, delivered)
            total_f_to_w[fp] += delivered
            ship_fw_executed[(fname, wname, fp)] = delivered

        for fp, val in total_f_to_w.items():
            data[f"factory_to_wh_{fp}"] = round(val, 2)

        # Step 7 — Ship FP: warehouses → markets
        # Computed AFTER fw deliveries have updated warehouse inventory
        use_ranked = (
            self.strategy is not None
            and self._disruption_active(t)
            and self.strategy.market_priority == "demand_ranked"
        )
        wm_plan = (self._ship_wm_demand_ranked(demand_samples) if use_ranked
                   else self._ship_wm_proportional(demand_samples))

        total_demand  = {fp: 0.0 for fp in FINAL_PRODUCTS}
        total_shipped = {fp: 0.0 for fp in FINAL_PRODUCTS}
        total_unmet   = {fp: 0.0 for fp in FINAL_PRODUCTS}
        market_received = {m.name: {fp: 0.0 for fp in FINAL_PRODUCTS} for m in self.markets}
        ship_wm_executed = {}

        for (wname, mname, fp), qty in wm_plan.items():
            warehouse = next((w for w in self.warehouses if w.name == wname), None)
            if warehouse is None or qty <= 0:
                ship_wm_executed[(wname, mname, fp)] = 0.0
                continue
            delivered = warehouse.ship(fp, qty)
            market_received[mname][fp] += delivered
            total_shipped[fp]          += delivered
            ship_wm_executed[(wname, mname, fp)] = delivered

        for m in self.markets:
            for fp in FINAL_PRODUCTS:
                total_demand[fp] += demand_samples[m.name][fp]
                total_unmet[fp]  += max(0.0, demand_samples[m.name][fp]
                                        - market_received[m.name][fp])

        for fp in FINAL_PRODUCTS:
            data[f"demand_{fp}"]  = round(total_demand[fp],  2)
            data[f"shipped_{fp}"] = round(total_shipped[fp], 2)
            data[f"unmet_{fp}"]   = round(total_unmet[fp],   2)

        # Step 8 — Return flow
        total_returns = {rp: 0.0 for rp in RECOVERED_PRODUCTS}
        for market in self.markets:
            returns = market.generate_returns(market_received[market.name])
            for rp in RECOVERED_PRODUCTS:
                total_returns[rp] += returns[rp]

        for rp in RECOVERED_PRODUCTS:
            if total_returns[rp] == 0:
                continue
            reman_caps = [
                sum(tech["capacity"] for _, tech in f.technologies.items()
                    if tech["type"] == "remanufacturing" and tech["input"] == rp)
                for f in self.factories
            ]
            total_cap = sum(reman_caps)
            for factory, cap in zip(self.factories, reman_caps):
                share = cap / total_cap if total_cap > 0 else 1.0 / len(self.factories)
                factory.receive_rp(rp, total_returns[rp] * share)

        for rp, val in total_returns.items():
            data[f"returns_{rp}"] = round(val, 2)

        # Step 9 — TBL metrics
        total_cost    = self._compute_cost(prod_executed, ship_fw_executed,
                                           ship_wm_executed, transport_mode)
        total_emi     = self._compute_emissions(prod_executed, ship_fw_executed,
                                                ship_wm_executed, transport_mode)
        social_impact = self._compute_social(self.factories, self.warehouses)

        total_dem = sum(total_demand[fp] for fp in FINAL_PRODUCTS)
        total_shp = sum(total_shipped[fp] for fp in FINAL_PRODUCTS)
        service_level = min((total_shp / total_dem * 100), 100.0) if total_dem > 0 else 100.0

        data["total_cost"]      = round(total_cost,    2)
        data["total_emissions"] = round(total_emi,     2)
        data["social_impact"]   = round(social_impact, 2)
        data["service_level"]   = round(service_level, 2)

        # Inventory snapshots
        data["supplier_inv"]  = round(sum(sum(s.inventory.values()) for s in self.suppliers), 2)
        data["factory_rm"]    = round(sum(sum(f.rm_inventory.values()) for f in self.factories), 2)
        data["factory_fp"]    = round(sum(sum(f.fp_inventory.values()) for f in self.factories), 2)
        data["factory_rp"]    = round(sum(sum(f.rp_inventory.values()) for f in self.factories), 2)
        data["warehouse_inv"] = round(sum(sum(w.inventory.values()) for w in self.warehouses), 2)

        self.records.append(data)
        return data

    def run(self):
        label = self.strategy.name if self.strategy else "Baseline LP Plan"
        print(f"  [{self.scenario.get('name', 'Baseline')}] {label}")
        for t in range(1, self.periods + 1):
            self.simulate_period(t)
        return pd.DataFrame(self.records)


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

def get_scenarios():
    return [
        {"name": "Baseline"},
        {"name": "Supplier Failure (periods 6-9)",
         "supplier_failure": {"node": "Supplier_A", "start": 6, "end": 9}},
        {"name": "Demand Spike +50% (periods 8-11)",
         "demand_spike": {"start": 8, "end": 11, "multiplier": 1.5}},
        {"name": "Factory 1 Downtime (periods 7-9)",
         "factory_downtime": {"node": "Factory_1", "start": 7, "end": 9}},
        {"name": "Return Rate Drop -60% (periods 5-12)",
         "return_rate_drop": {"start": 5, "end": 12, "factor": 0.4}},
    ]
