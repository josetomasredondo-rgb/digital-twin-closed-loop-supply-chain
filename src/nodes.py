# =============================================================
# NODE CLASSES
# =============================================================

import random
from data import FINAL_PRODUCTS, TECHNOLOGIES


class SupplierNode:
    """
    Supplies raw materials to factories.
    Each supplier can carry multiple RM types.
    Each period it restocks and then ships to factories on request.
    """
    def __init__(self, name: str, inventory: dict, capacity: dict, restock_rate: dict):
        """
        Parameters
        ----------
        name         : node name (must match DISTANCE_TABLE index)
        inventory    : dict  {rm_type: initial_stock},   e.g. {"RM_1": 150}
        capacity     : dict  {rm_type: max_stock}
        restock_rate : dict  {rm_type: units_restocked_per_period}
        """
        self.name = name
        self.inventory    = inventory.copy()
        self.capacity     = capacity.copy()
        self.restock_rate = restock_rate.copy()

    def restock(self):
        """Replenish each RM type up to its capacity."""
        for rm in self.inventory:
            self.inventory[rm] = min(
                self.capacity[rm],
                self.inventory[rm] + self.restock_rate.get(rm, 0)
            )

    def ship(self, rm_type: str, quantity: float) -> float:
        """Ship a specific RM type; limited by available stock."""
        available = self.inventory.get(rm_type, 0)
        shipped   = min(max(0.0, quantity), available)
        self.inventory[rm_type] = available - shipped
        return shipped


class FactoryNode:
    """
    Produces final products using:
      - Production technologies     : RM  --> FP
      - Remanufacturing technologies: RP  --> FP  (separate process)

    The technologies available to THIS factory are passed in as a list
    of keys from the global TECHNOLOGIES dict.
    """
    def __init__(self, name: str, rm_inventory: dict, fp_inventory: dict,
                 rm_capacity: dict, fp_capacity: dict, technology_ids: list):
        """
        Parameters
        ----------
        name            : node name
        rm_inventory    : {rm_type: initial_stock}
        fp_inventory    : {fp_type: initial_stock}
        rm_capacity     : {rm_type: max_storage}
        fp_capacity     : {fp_type: max_storage}
        technology_ids  : list of technology keys, e.g. ["TECH_P1", "TECH_R1"]
        """
        self.name         = name
        self.rm_inventory = rm_inventory.copy()
        self.fp_inventory = fp_inventory.copy()
        self.rm_capacity  = rm_capacity.copy()
        self.fp_capacity  = fp_capacity.copy()
        self.technologies = {tid: TECHNOLOGIES[tid] for tid in technology_ids}

        # RP stock: recovered products waiting to be remanufactured
        # keyed by FP type (since RP is a used version of FP)
        self.rp_inventory = {fp: 0.0 for fp in FINAL_PRODUCTS}

    def receive_rm(self, rm_type: str, quantity: float) -> float:
        """Accept raw material from a supplier."""
        space    = self.rm_capacity.get(rm_type, 0) - self.rm_inventory.get(rm_type, 0)
        received = min(max(0.0, quantity), space)
        self.rm_inventory[rm_type] = self.rm_inventory.get(rm_type, 0) + received
        return received

    def receive_rp(self, fp_type: str, quantity: float) -> float:
        """Accept recovered product (RP) returned from a market."""
        received = max(0.0, quantity)
        self.rp_inventory[fp_type] = self.rp_inventory.get(fp_type, 0) + received
        return received

    def run_production(self) -> dict:
        """
        Run all PRODUCTION technologies (RM -> FP).
        Each technology produces as much as possible given:
          - available RM input
          - technology capacity
          - available FP storage space
        Returns dict of {fp_type: units_produced}
        """
        produced = {fp: 0.0 for fp in FINAL_PRODUCTS}
        for tid, tech in self.technologies.items():
            if tech["type"] != "production":
                continue
            rm_avail  = self.rm_inventory.get(tech["input"], 0)
            fp_space  = self.fp_capacity.get(tech["output"], 0) - self.fp_inventory.get(tech["output"], 0)
            # max output limited by RM stock, technology capacity, and storage space
            max_output = min(
                rm_avail / tech["input_rate"],
                tech["capacity"],
                fp_space
            )
            output = max(0.0, max_output)
            self.rm_inventory[tech["input"]]  -= output * tech["input_rate"]
            self.fp_inventory[tech["output"]] = self.fp_inventory.get(tech["output"], 0) + output
            produced[tech["output"]]          += output
        return produced

    def run_remanufacturing(self) -> dict:
        """
        Run all REMANUFACTURING technologies (RP -> FP).
        Each technology produces as much as possible given:
          - available RP input
          - technology capacity
          - available FP storage space
        Returns dict of {fp_type: units_remanufactured}
        """
        remanufactured = {fp: 0.0 for fp in FINAL_PRODUCTS}
        for tid, tech in self.technologies.items():
            if tech["type"] != "remanufacturing":
                continue
            rp_avail = self.rp_inventory.get(tech["input"], 0)
            fp_space = self.fp_capacity.get(tech["output"], 0) - self.fp_inventory.get(tech["output"], 0)
            max_output = min(
                rp_avail / tech["input_rate"],
                tech["capacity"],
                fp_space
            )
            output = max(0.0, max_output)
            self.rp_inventory[tech["input"]]  -= output * tech["input_rate"]
            self.fp_inventory[tech["output"]] = self.fp_inventory.get(tech["output"], 0) + output
            remanufactured[tech["output"]]    += output
        return remanufactured

    def ship_fp(self, fp_type: str, quantity: float) -> float:
        """Ship finished product to a warehouse."""
        available = self.fp_inventory.get(fp_type, 0)
        shipped   = min(max(0.0, quantity), available)
        self.fp_inventory[fp_type] = available - shipped
        return shipped


class WarehouseNode:
    """
    Stores finished products and ships them to markets.
    Handles multiple FP types.
    """
    def __init__(self, name: str, inventory: dict, capacity: dict):
        """
        Parameters
        ----------
        inventory : {fp_type: initial_stock}
        capacity  : {fp_type: max_stock}
        """
        self.name      = name
        self.inventory = inventory.copy()
        self.capacity  = capacity.copy()

    def receive(self, fp_type: str, quantity: float) -> float:
        space    = self.capacity.get(fp_type, 0) - self.inventory.get(fp_type, 0)
        received = min(max(0.0, quantity), space)
        self.inventory[fp_type] = self.inventory.get(fp_type, 0) + received
        return received

    def ship(self, fp_type: str, quantity: float) -> float:
        available = self.inventory.get(fp_type, 0)
        shipped   = min(max(0.0, quantity), available)
        self.inventory[fp_type] = available - shipped
        return shipped


class MarketNode:
    """
    Generates stochastic demand for each FP type.
    Returns a fraction of received products back to factories as RP.
    """
    def __init__(self, name: str, base_demand: dict, demand_std: dict, return_rate: dict):
        """
        Parameters
        ----------
        base_demand : {fp_type: average_demand_per_period}
        demand_std  : {fp_type: std_deviation_of_demand}
        return_rate : {fp_type: fraction_returned_as_RP}
        """
        self.name        = name
        self.base_demand = base_demand.copy()
        self.demand_std  = demand_std.copy()
        self.return_rate = return_rate.copy()

    def generate_demand(self) -> dict:
        """Sample demand for each FP type."""
        return {
            fp: max(0.0, random.gauss(self.base_demand.get(fp, 0), self.demand_std.get(fp, 0)))
            for fp in FINAL_PRODUCTS
        }

    def generate_returns(self, received: dict) -> dict:
        """Calculate RP quantities based on what was actually received."""
        return {
            fp: received.get(fp, 0) * self.return_rate.get(fp, 0)
            for fp in FINAL_PRODUCTS
        }