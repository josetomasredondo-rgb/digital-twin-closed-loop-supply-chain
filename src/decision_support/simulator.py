import random
import pandas as pd
from .constants import RAW_MATERIALS, FINAL_PRODUCTS
from .nodes import (SupplierNode, FactoryNode, WarehouseNode, MarketNode,
                    CustomerNode, AirportNode, PortNode)
from .transportation import DEFAULT_TRANSPORT_MODES
from .optimizer import SupplyChainOptimizer


class ClosedLoopSimulator:
    def __init__(self, periods=24, scenario=None):
        self.periods   = periods
        self.scenario  = scenario or {}
        self.optimizer = SupplyChainOptimizer()
        self.transport_modes = DEFAULT_TRANSPORT_MODES.copy()
        self._build_nodes()
        self.records = []

    def _build_nodes(self):
        # 3 Suppliers
        self.suppliers = [
            SupplierNode("Supplier_A",
                inventory={"RM_1": 150}, capacity={"RM_1": 250},
                restock_rate={"RM_1": 100}),
            SupplierNode("Supplier_B",
                inventory={"RM_2": 120}, capacity={"RM_2": 220},
                restock_rate={"RM_2": 90}),
            SupplierNode("Supplier_C",
                inventory={"RM_1": 100, "RM_2": 80}, capacity={"RM_1": 200, "RM_2": 180},
                restock_rate={"RM_1": 80, "RM_2": 70}),
        ]

        # 3 Factories
        self.factories = [
            FactoryNode("Factory_1",
                rm_inventory={"RM_1": 80,  "RM_2":  0},
                fp_inventory={"FP_A": 30,  "FP_B":  0, "FP_C": 0},
                rm_capacity={"RM_1": 200, "RM_2":  0},
                fp_capacity={"FP_A": 150, "FP_B":  0, "FP_C": 120},
                technology_ids=["TECH_P1", "TECH_P3", "TECH_R1", "TECH_R3"]),
            FactoryNode("Factory_2",
                rm_inventory={"RM_1":  0,  "RM_2": 70},
                fp_inventory={"FP_A":  0,  "FP_B": 25, "FP_C": 0},
                rm_capacity={"RM_1":  0,  "RM_2": 180},
                fp_capacity={"FP_A":  0,  "FP_B": 130, "FP_C": 110},
                technology_ids=["TECH_P2", "TECH_P3", "TECH_R2", "TECH_R3"]),
            FactoryNode("Factory_3",
                rm_inventory={"RM_1": 60,  "RM_2": 50},
                fp_inventory={"FP_A": 20,  "FP_B": 15, "FP_C": 10},
                rm_capacity={"RM_1": 180, "RM_2": 170},
                fp_capacity={"FP_A": 140, "FP_B": 120, "FP_C": 100},
                technology_ids=["TECH_P1", "TECH_P2", "TECH_P3", "TECH_R1", "TECH_R2", "TECH_R3"]),
        ]

        # 5 Warehouses
        self.warehouses = [
            WarehouseNode("Warehouse_1",
                inventory={"FP_A": 40, "FP_B": 30, "FP_C": 25},
                capacity={"FP_A": 150, "FP_B": 150, "FP_C": 140}),
            WarehouseNode("Warehouse_2",
                inventory={"FP_A": 35, "FP_B": 25, "FP_C": 20},
                capacity={"FP_A": 130, "FP_B": 130, "FP_C": 120}),
            WarehouseNode("Warehouse_3",
                inventory={"FP_A": 30, "FP_B": 20, "FP_C": 15},
                capacity={"FP_A": 120, "FP_B": 120, "FP_C": 110}),
            WarehouseNode("Warehouse_4",
                inventory={"FP_A": 25, "FP_B": 35, "FP_C": 30},
                capacity={"FP_A": 140, "FP_B": 140, "FP_C": 130}),
            WarehouseNode("Warehouse_5",
                inventory={"FP_A": 28, "FP_B": 22, "FP_C": 18},
                capacity={"FP_A": 125, "FP_B": 125, "FP_C": 115}),
        ]

        # 6 Customers
        self.customers = [
            CustomerNode("Customer_1",
                base_demand={"FP_A": 30, "FP_B": 25, "FP_C": 20},
                demand_std={"FP_A":  5, "FP_B":  4, "FP_C":  3},
                return_rate={"FP_A": 0.20, "FP_B": 0.18, "FP_C": 0.16}),
            CustomerNode("Customer_2",
                base_demand={"FP_A": 25, "FP_B": 20, "FP_C": 18},
                demand_std={"FP_A":  4, "FP_B":  4, "FP_C":  3},
                return_rate={"FP_A": 0.22, "FP_B": 0.20, "FP_C": 0.17}),
            CustomerNode("Customer_3",
                base_demand={"FP_A": 20, "FP_B": 18, "FP_C": 15},
                demand_std={"FP_A":  4, "FP_B":  3, "FP_C":  3},
                return_rate={"FP_A": 0.18, "FP_B": 0.15, "FP_C": 0.14}),
            CustomerNode("Customer_4",
                base_demand={"FP_A": 28, "FP_B": 22, "FP_C": 19},
                demand_std={"FP_A":  5, "FP_B":  4, "FP_C":  4},
                return_rate={"FP_A": 0.19, "FP_B": 0.17, "FP_C": 0.15}),
            CustomerNode("Customer_5",
                base_demand={"FP_A": 22, "FP_B": 18, "FP_C": 16},
                demand_std={"FP_A":  4, "FP_B":  3, "FP_C":  3},
                return_rate={"FP_A": 0.21, "FP_B": 0.19, "FP_C": 0.16}),
            CustomerNode("Customer_6",
                base_demand={"FP_A": 26, "FP_B": 24, "FP_C": 21},
                demand_std={"FP_A":  5, "FP_B":  4, "FP_C":  4},
                return_rate={"FP_A": 0.20, "FP_B": 0.18, "FP_C": 0.15}),
        ]

        # 3 Airports
        self.airports = [
            AirportNode("Airport_North",
                inventory={"FP_A": 20, "FP_B": 15, "FP_C": 12},
                capacity={"FP_A": 100, "FP_B": 100, "FP_C": 90},
                region="North"),
            AirportNode("Airport_Central",
                inventory={"FP_A": 15, "FP_B": 10, "FP_C": 8},
                capacity={"FP_A": 80, "FP_B": 80, "FP_C": 70},
                region="Central"),
            AirportNode("Airport_South",
                inventory={"FP_A": 18, "FP_B": 12, "FP_C": 10},
                capacity={"FP_A": 90, "FP_B": 90, "FP_C": 80},
                region="South"),
        ]

        # 3 Ports
        self.ports = [
            PortNode("Port_West",
                inventory={"FP_A": 50, "FP_B": 40, "FP_C": 35},
                capacity={"FP_A": 300, "FP_B": 300, "FP_C": 280},
                region="West"),
            PortNode("Port_East",
                inventory={"FP_A": 45, "FP_B": 35, "FP_C": 30},
                capacity={"FP_A": 280, "FP_B": 280, "FP_C": 260},
                region="East"),
            PortNode("Port_South",
                inventory={"FP_A": 40, "FP_B": 30, "FP_C": 25},
                capacity={"FP_A": 250, "FP_B": 250, "FP_C": 230},
                region="South"),
        ]

        # Keep markets reference for backwards compatibility
        self.markets = self.customers

    def _apply_disruption(self, t):
        s = self.scenario

        if "supplier_failure" in s:
            sf = s["supplier_failure"]
            for sup in self.suppliers:
                if sup.name == sf["node"]:
                    if sf["start"] <= t <= sf["end"]:
                        sup.restock_rate = {rm: 0 for rm in sup.restock_rate}
                    elif t == sf["end"] + 1:
                        sup.restock_rate = sf["original_restock"]

        if "factory_downtime" in s:
            fd = s["factory_downtime"]
            for fac in self.factories:
                if fac.name == fd["node"]:
                    fac.active = not (fd["start"] <= t <= fd["end"])

        if "demand_spike" in s:
            ds = s["demand_spike"]
            for m in self.markets:
                if ds["start"] <= t <= ds["end"]:
                    m.demand_multiplier = ds["multiplier"]
                else:
                    m.demand_multiplier = 1.0

        if "return_rate_drop" in s:
            rd = s["return_rate_drop"]
            for m in self.markets:
                if rd["start"] <= t <= rd["end"]:
                    m.return_rate = {fp: r * rd["factor"]
                                     for fp, r in m.return_rate.items()}
                elif t == rd["end"] + 1:
                    m.return_rate = rd["original_rates"][m.name]

    def simulate_period(self, t):
        data = {"period": t}
        self._apply_disruption(t)

        for s in self.suppliers:
            s.restock()

        total_rm_shipped = {rm: 0.0 for rm in RAW_MATERIALS}
        for supplier in self.suppliers:
            for rm_type in supplier.inventory:
                eligible = [f for f in self.factories
                            if f.active and rm_type in f.rm_capacity
                            and f.rm_capacity[rm_type] > 0]
                if not eligible:
                    continue
                for factory in eligible:
                    needed    = max(0.0, factory.rm_capacity[rm_type] * 0.8
                                   - factory.rm_inventory.get(rm_type, 0))
                    n_sup     = sum(1 for s in self.suppliers if rm_type in s.inventory)
                    delivered = supplier.ship(rm_type, needed / max(n_sup, 1))
                    factory.receive_rm(rm_type, delivered)
                    total_rm_shipped[rm_type] += delivered

        for rm, val in total_rm_shipped.items():
            data[f"rm_shipped_{rm}"] = round(val, 2)

        prod_plan, ship_fw_plan, ship_wm_plan, obj_vals = self.optimizer.optimize(
            self.factories, self.warehouses, self.markets, self.suppliers
        )

        total_produced       = {fp: 0.0 for fp in FINAL_PRODUCTS}
        total_remanufactured = {fp: 0.0 for fp in FINAL_PRODUCTS}
        for (fname, tid), qty in prod_plan.items():
            factory = next(f for f in self.factories if f.name == fname)
            actual  = factory.produce(tid, qty)
            tech    = factory.technologies[tid]
            if tech["type"] == "production":
                total_produced[tech["output"]] += actual
            else:
                total_remanufactured[tech["output"]] += actual

        for fp in FINAL_PRODUCTS:
            data[f"produced_{fp}"]       = round(total_produced[fp], 2)
            data[f"remanufactured_{fp}"] = round(total_remanufactured[fp], 2)

        total_f_to_w = {fp: 0.0 for fp in FINAL_PRODUCTS}
        for (fname, wname, fp), qty in ship_fw_plan.items():
            factory   = next(f for f in self.factories   if f.name == fname)
            warehouse = next(w for w in self.warehouses  if w.name == wname)
            delivered = factory.ship_fp(fp, qty)
            warehouse.receive(fp, delivered)
            total_f_to_w[fp] += delivered

        for fp, val in total_f_to_w.items():
            data[f"factory_to_wh_{fp}"] = round(val, 2)

        total_demand  = {fp: 0.0 for fp in FINAL_PRODUCTS}
        total_shipped = {fp: 0.0 for fp in FINAL_PRODUCTS}
        total_unmet   = {fp: 0.0 for fp in FINAL_PRODUCTS}
        market_received = {m.name: {fp: 0.0 for fp in FINAL_PRODUCTS}
                           for m in self.markets}

        for (wname, mname, fp), qty in ship_wm_plan.items():
            warehouse = next(w for w in self.warehouses if w.name == wname)
            market    = next(m for m in self.markets    if m.name == mname)
            delivered = warehouse.ship(fp, qty)
            market_received[mname][fp] += delivered
            total_shipped[fp]          += delivered

        for m in self.markets:
            demand = obj_vals["demand"][m.name]
            for fp in FINAL_PRODUCTS:
                total_demand[fp] += demand[fp]
                total_unmet[fp]  += max(0.0, demand[fp] - market_received[m.name][fp])

        for fp in FINAL_PRODUCTS:
            data[f"demand_{fp}"]  = round(total_demand[fp],  2)
            data[f"shipped_{fp}"] = round(total_shipped[fp], 2)
            data[f"unmet_{fp}"]   = round(total_unmet[fp],   2)

        total_returns = {fp: 0.0 for fp in FINAL_PRODUCTS}
        for market in self.markets:
            returns = market.generate_returns(market_received[market.name])
            for fp_type in FINAL_PRODUCTS:
                total_returns[fp_type] += returns[fp_type]
                per_factory = returns[fp_type] / max(len(self.factories), 1)
                for factory in self.factories:
                    factory.receive_rp(fp_type, per_factory)

        for fp, val in total_returns.items():
            data[f"returns_{fp}"] = round(val, 2)

        data["opt_status"]    = obj_vals["status"]
        data["opt_cost"]      = round(obj_vals["cost"],      2)
        data["opt_emissions"] = round(obj_vals["emissions"], 2)
        data["opt_unmet"]     = round(obj_vals["unmet"],     2)

        data["supplier_inv"]  = round(sum(sum(s.inventory.values()) for s in self.suppliers), 2)
        data["factory_rm"]    = round(sum(sum(f.rm_inventory.values()) for f in self.factories), 2)
        data["factory_fp"]    = round(sum(sum(f.fp_inventory.values()) for f in self.factories), 2)
        data["factory_rp"]    = round(sum(sum(f.rp_inventory.values()) for f in self.factories), 2)
        data["warehouse_inv"] = round(sum(sum(w.inventory.values()) for w in self.warehouses), 2)

        self.records.append(data)
        return data

    def run(self):
        scenario_name = self.scenario.get("name", "Baseline")
        print(f"\n{'='*80}")
        print(f"SCENARIO: {scenario_name}")
        print(f"{'='*80}")
        for t in range(1, self.periods + 1):
            d = self.simulate_period(t)
            print(f"  Period {t:>2} | "
                  f"Unmet: FP_A={d['unmet_FP_A']:>4.1f} FP_B={d['unmet_FP_B']:>4.1f} | "
                  f"Cost: {d['opt_cost']:>7.1f}€ | "
                  f"Emissions: {d['opt_emissions']:>6.1f}kg | "
                  f"Status: {d['opt_status']}")
        print(f"{'='*80}")
        return pd.DataFrame(self.records)


def get_scenarios(markets):
    return [
        {"name": "Baseline"},
        {"name": "Supplier Failure (periods 6-9)",
         "supplier_failure": {
             "node": "Supplier_A", "start": 6, "end": 9,
             "original_restock": {"RM_1": 100}
         }},
        {"name": "Demand Spike +50% (periods 8-11)",
         "demand_spike": {"start": 8, "end": 11, "multiplier": 1.5}},
        {"name": "Factory 1 Downtime (periods 7-9)",
         "factory_downtime": {"node": "Factory_1", "start": 7, "end": 9}},
        {"name": "Return Rate Drop -60% (periods 5-12)",
         "return_rate_drop": {
             "start": 5, "end": 12, "factor": 0.4,
             "original_rates": {m.name: m.return_rate.copy() for m in markets}
         }},
    ]
