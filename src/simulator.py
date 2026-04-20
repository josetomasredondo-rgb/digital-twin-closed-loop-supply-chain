# =============================================================
# SIMULATOR
# =============================================================

import pandas as pd
from data import RAW_MATERIALS, FINAL_PRODUCTS
from nodes import SupplierNode, FactoryNode, WarehouseNode, MarketNode


class ClosedLoopSimulator:
    """
    Runs the closed-loop supply chain simulation period by period.

    Each period:
      1. Suppliers restock
      2. Suppliers ship RM to factories
      3. Factories run production  (RM  -> FP)
      4. Factories run remanufacturing (RP -> FP)
      5. Factories ship FP to warehouses
      6. Warehouses fulfill market demand
      7. Markets generate RP returns -> sent back to factories
      8. Record everything
    """

    def __init__(self, periods: int = 24):
        self.periods = periods

        # --- Suppliers ---
        self.suppliers = [
            SupplierNode("Supplier_A",
                inventory    = {"RM_1": 150},
                capacity     = {"RM_1": 250},
                restock_rate = {"RM_1": 100}),
            SupplierNode("Supplier_B",
                inventory    = {"RM_2": 120},
                capacity     = {"RM_2": 220},
                restock_rate = {"RM_2": 90}),
        ]

        # --- Factories ---
        # Factory_1 has production tech for FP_A and remanufacturing for FP_A
        # Factory_2 has production tech for FP_B and remanufacturing for FP_B
        self.factories = [
            FactoryNode("Factory_1",
                rm_inventory    = {"RM_1": 80,  "RM_2":  0},
                fp_inventory    = {"FP_A": 30,  "FP_B":  0},
                rm_capacity     = {"RM_1": 200, "RM_2":  0},
                fp_capacity     = {"FP_A": 150, "FP_B":  0},
                technology_ids  = ["TECH_P1", "TECH_R1"]),
 
            FactoryNode("Factory_2",
                rm_inventory    = {"RM_1":  0,  "RM_2": 70},
                fp_inventory    = {"FP_A":  0,  "FP_B": 25},
                rm_capacity     = {"RM_1":  0,  "RM_2": 180},
                fp_capacity     = {"FP_A":  0,  "FP_B": 130},
                technology_ids  = ["TECH_P2", "TECH_R2"]),
        ]

        # --- Warehouses ---
        self.warehouses = [
            WarehouseNode("Warehouse_1",
                inventory = {"FP_A": 40, "FP_B": 30},
                capacity  = {"FP_A": 150, "FP_B": 150}),
            WarehouseNode("Warehouse_2",
                inventory = {"FP_A": 35, "FP_B": 25},
                capacity  = {"FP_A": 130, "FP_B": 130}),
            WarehouseNode("Warehouse_3",
                inventory = {"FP_A": 30, "FP_B": 20},
                capacity  = {"FP_A": 120, "FP_B": 120}),
        ]

        # --- Markets ---
        self.markets = [
            MarketNode("Market_A",
                base_demand = {"FP_A": 30, "FP_B": 25},
                demand_std  = {"FP_A":  5, "FP_B":  4},
                return_rate = {"FP_A": 0.20, "FP_B": 0.18}),
            MarketNode("Market_B",
                base_demand = {"FP_A": 25, "FP_B": 20},
                demand_std  = {"FP_A":  4, "FP_B":  4},
                return_rate = {"FP_A": 0.22, "FP_B": 0.20}),
            MarketNode("Market_C",
                base_demand = {"FP_A": 20, "FP_B": 18},
                demand_std  = {"FP_A":  4, "FP_B":  3},
                return_rate = {"FP_A": 0.18, "FP_B": 0.15}),
        ]

        self.records = []

    # ----------------------------------------------------------
    # HELPER: split a quantity evenly across a list of nodes
    # ----------------------------------------------------------
    @staticmethod
    def _split(total: float, n: int) -> float:
        return total / n if n > 0 else 0.0

    def simulate_period(self, t: int):
        data = {"period": t}

        # === STEP 1: Suppliers restock ===
        for s in self.suppliers:
            s.restock()

        # === STEP 2: Suppliers ship RM to factories ===
        # Each supplier ships its RM type to every factory that needs it
        total_rm_shipped = {rm: 0.0 for rm in RAW_MATERIALS}
        for supplier in self.suppliers:
            for rm_type in supplier.inventory:
                # Factories that have capacity for this RM
                eligible = [f for f in self.factories if rm_type in f.rm_capacity and f.rm_capacity[rm_type] > 0]
                if not eligible:
                    continue
                for factory in eligible:
                    needed   = max(0.0, factory.rm_capacity[rm_type] * 0.8 - factory.rm_inventory.get(rm_type, 0))
                    per_supp = self._split(needed, sum(1 for s in self.suppliers if rm_type in s.inventory))
                    delivered = supplier.ship(rm_type, per_supp)
                    factory.receive_rm(rm_type, delivered)
                    total_rm_shipped[rm_type] += delivered

        for rm, val in total_rm_shipped.items():
            data[f"rm_shipped_{rm}"] = round(val, 2)

        # === STEP 3: Factories run PRODUCTION (RM -> FP) ===
        total_produced = {fp: 0.0 for fp in FINAL_PRODUCTS}
        for factory in self.factories:
            produced = factory.run_production()
            for fp, qty in produced.items():
                total_produced[fp] += qty

        for fp, val in total_produced.items():
            data[f"produced_{fp}"] = round(val, 2)

        # === STEP 4: Factories run REMANUFACTURING (RP -> FP) ===
        total_remanufactured = {fp: 0.0 for fp in FINAL_PRODUCTS}
        for factory in self.factories:
            reman = factory.run_remanufacturing()
            for fp, qty in reman.items():
                total_remanufactured[fp] += qty

        for fp, val in total_remanufactured.items():
            data[f"remanufactured_{fp}"] = round(val, 2)

        # === STEP 5: Factories ship FP to warehouses ===
        total_f_to_w = {fp: 0.0 for fp in FINAL_PRODUCTS}
        for warehouse in self.warehouses:
            for fp_type in FINAL_PRODUCTS:
                needed     = max(0.0, warehouse.capacity[fp_type] * 0.8 - warehouse.inventory.get(fp_type, 0))
                per_factory = self._split(needed, len(self.factories))
                for factory in self.factories:
                    delivered = factory.ship_fp(fp_type, per_factory)
                    warehouse.receive(fp_type, delivered)
                    total_f_to_w[fp_type] += delivered

        for fp, val in total_f_to_w.items():
            data[f"factory_to_wh_{fp}"] = round(val, 2)

        # === STEP 6: Warehouses fulfill market demand ===
        total_demand  = {fp: 0.0 for fp in FINAL_PRODUCTS}
        total_shipped = {fp: 0.0 for fp in FINAL_PRODUCTS}
        total_unmet   = {fp: 0.0 for fp in FINAL_PRODUCTS}
        market_received = {m.name: {fp: 0.0 for fp in FINAL_PRODUCTS} for m in self.markets}

        for market in self.markets:
            demand = market.generate_demand()
            for fp_type in FINAL_PRODUCTS:
                total_demand[fp_type] += demand[fp_type]
                per_wh = self._split(demand[fp_type], len(self.warehouses))
                received = 0.0
                for warehouse in self.warehouses:
                    received += warehouse.ship(fp_type, per_wh)
                total_shipped[fp_type]                  += received
                total_unmet[fp_type]                    += max(0.0, demand[fp_type] - received)
                market_received[market.name][fp_type]   += received

        for fp in FINAL_PRODUCTS:
            data[f"demand_{fp}"]  = round(total_demand[fp],  2)
            data[f"shipped_{fp}"] = round(total_shipped[fp], 2)
            data[f"unmet_{fp}"]   = round(total_unmet[fp],   2)

        # === STEP 7: Markets return RP to factories ===
        total_returns = {fp: 0.0 for fp in FINAL_PRODUCTS}
        for market in self.markets:
            returns = market.generate_returns(market_received[market.name])
            for fp_type in FINAL_PRODUCTS:
                total_returns[fp_type] += returns[fp_type]
                per_factory = self._split(returns[fp_type], len(self.factories))
                for factory in self.factories:
                    factory.receive_rp(fp_type, per_factory)

        for fp, val in total_returns.items():
            data[f"returns_{fp}"] = round(val, 2)

        # === STEP 8: Inventory snapshots ===
        data["supplier_inv_total"]  = round(sum(sum(s.inventory.values()) for s in self.suppliers), 2)
        data["factory_rm_total"]    = round(sum(sum(f.rm_inventory.values()) for f in self.factories), 2)
        data["factory_fp_total"]    = round(sum(sum(f.fp_inventory.values()) for f in self.factories), 2)
        data["factory_rp_total"]    = round(sum(sum(f.rp_inventory.values()) for f in self.factories), 2)
        data["warehouse_inv_total"] = round(sum(sum(w.inventory.values()) for w in self.warehouses), 2)

        self.records.append(data)

        print(
            f"Period {t:>2} | "
            f"Demand FP_A: {data['demand_FP_A']:>5.1f}  FP_B: {data['demand_FP_B']:>5.1f} | "
            f"Unmet FP_A: {data['unmet_FP_A']:>4.1f}  FP_B: {data['unmet_FP_B']:>4.1f} | "
            f"Prod FP_A: {data['produced_FP_A']:>5.1f}  FP_B: {data['produced_FP_B']:>5.1f} | "
            f"Reman FP_A: {data['remanufactured_FP_A']:>4.1f}  FP_B: {data['remanufactured_FP_B']:>4.1f}"
        )

    def run(self) -> pd.DataFrame:
        print("=" * 110)
        print("CLOSED-LOOP SUPPLY CHAIN SIMULATION — CHEMICALS INDUSTRY")
        print(f"Suppliers: {len(self.suppliers)} | Factories: {len(self.factories)} | "
              f"Warehouses: {len(self.warehouses)} | Markets: {len(self.markets)}")
        print(f"Raw Materials: {RAW_MATERIALS} | Final Products: {FINAL_PRODUCTS}")
        print(f"Periods: {self.periods}")
        print("=" * 110)
        for t in range(1, self.periods + 1):
            self.simulate_period(t)
        print("=" * 110)
        print("Simulation complete.\n")
        return pd.DataFrame(self.records)