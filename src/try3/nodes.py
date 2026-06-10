"""
nodes.py — Supply chain node definitions for the Digital Twin DSS.

FIX: SupplierNode now has an `active` flag so that disrupted suppliers
     block all shipments (not just restock), correctly modelling supplier failure.
"""

import random
from .constants import FINAL_PRODUCTS, RECOVERED_PRODUCTS, TECHNOLOGIES


class SupplierNode:
    def __init__(self, name, inventory, capacity, restock_rate, region=""):
        self.name               = name
        self.inventory          = inventory.copy()
        self.capacity           = capacity.copy()
        self.restock_rate       = restock_rate.copy()
        self._base_restock_rate = restock_rate.copy()
        self.region             = region
        # FIX: explicit active flag so ship() returns 0 when disrupted
        self.active             = True

    def restock(self):
        if not self.active:
            return
        for rm in self.inventory:
            self.inventory[rm] = min(
                self.capacity[rm],
                self.inventory[rm] + self.restock_rate.get(rm, 0)
            )

    def ship(self, rm_type, quantity):
        # FIX: disrupted supplier ships nothing
        if not self.active:
            return 0.0
        available = self.inventory.get(rm_type, 0)
        shipped   = min(max(0.0, quantity), available)
        self.inventory[rm_type] = available - shipped
        return shipped

    def disrupt(self, rm_type=None):
        """
        FIX: set active=False (stops ALL shipments) and zero restock rate.
        Previously only zeroed restock_rate, leaving existing inventory
        available for shipping — disruption had zero effect on supply.
        """
        self.active = False
        if rm_type:
            self.restock_rate[rm_type] = 0
        else:
            self.restock_rate = {rm: 0 for rm in self.restock_rate}

    def restore(self, rm_type=None):
        self.active = True
        if rm_type:
            self.restock_rate[rm_type] = self._base_restock_rate[rm_type]
        else:
            self.restock_rate = self._base_restock_rate.copy()

    def __repr__(self):
        return f"SupplierNode({self.name}, active={self.active}, inv={self.inventory})"


class FactoryNode:
    def __init__(self, name, rm_inventory, fp_inventory,
                 rm_capacity, fp_capacity, technology_ids,
                 employees=0, region=""):
        self.name         = name
        self.rm_inventory = rm_inventory.copy()
        self.fp_inventory = fp_inventory.copy()
        self.rm_capacity  = rm_capacity.copy()
        self.fp_capacity  = fp_capacity.copy()
        self.technologies = {tid: TECHNOLOGIES[tid] for tid in technology_ids
                             if tid in TECHNOLOGIES}
        self.rp_inventory = {rp: 0.0 for rp in RECOVERED_PRODUCTS}
        self.employees    = employees
        self.region       = region
        self.active       = True

    def receive_rm(self, rm_type, quantity):
        space    = self.rm_capacity.get(rm_type, 0) - self.rm_inventory.get(rm_type, 0)
        received = min(max(0.0, quantity), space)
        self.rm_inventory[rm_type] = self.rm_inventory.get(rm_type, 0) + received
        return received

    def receive_rp(self, rp_type, quantity):
        received = max(0.0, quantity)
        self.rp_inventory[rp_type] = self.rp_inventory.get(rp_type, 0) + received
        return received

    def produce(self, tech_id, quantity):
        if not self.active or tech_id not in self.technologies:
            return 0.0
        tech     = self.technologies[tech_id]
        quantity = max(0.0, quantity)
        fp_space = self.fp_capacity.get(tech["output"], 0) - self.fp_inventory.get(tech["output"], 0)
        if tech["type"] == "production":
            rm_avail = self.rm_inventory.get(tech["input"], 0)
            max_out  = min(quantity, rm_avail / tech["input_rate"], tech["capacity"], fp_space)
            output   = max(0.0, max_out)
            self.rm_inventory[tech["input"]] = self.rm_inventory.get(tech["input"], 0) - output * tech["input_rate"]
        else:
            rp_avail = self.rp_inventory.get(tech["input"], 0)
            max_out  = min(quantity, rp_avail / tech["input_rate"], tech["capacity"], fp_space)
            output   = max(0.0, max_out)
            self.rp_inventory[tech["input"]] = self.rp_inventory.get(tech["input"], 0) - output * tech["input_rate"]
        self.fp_inventory[tech["output"]] = self.fp_inventory.get(tech["output"], 0) + output
        return output

    def ship_fp(self, fp_type, quantity):
        if not self.active:
            return 0.0
        available = self.fp_inventory.get(fp_type, 0)
        shipped   = min(max(0.0, quantity), available)
        self.fp_inventory[fp_type] = available - shipped
        return shipped

    def disrupt(self):
        self.active = False

    def restore(self):
        self.active = True

    def __repr__(self):
        return f"FactoryNode({self.name}, active={self.active}, employees={self.employees})"


class WarehouseNode:
    def __init__(self, name, inventory, capacity, employees=0, region=""):
        self.name               = name
        self.inventory          = inventory.copy()
        self.capacity           = capacity.copy()
        self.employees          = employees
        self.region             = region
        self.throughput_factor  = 1.0
        self._base_throughput   = 1.0

    def receive(self, fp_type, quantity):
        space    = self.capacity.get(fp_type, 0) - self.inventory.get(fp_type, 0)
        received = min(max(0.0, quantity), space)
        self.inventory[fp_type] = self.inventory.get(fp_type, 0) + received
        return received

    def ship(self, fp_type, quantity):
        available = self.inventory.get(fp_type, 0)
        shipped   = min(max(0.0, quantity), available) * self.throughput_factor
        self.inventory[fp_type] = available - shipped
        return shipped

    def disrupt_throughput(self, factor):
        self.throughput_factor = factor

    def restore_throughput(self):
        self.throughput_factor = self._base_throughput

    def __repr__(self):
        return f"WarehouseNode({self.name}, region={self.region})"


class MarketNode:
    def __init__(self, name, base_demand, demand_std, return_rate,
                 demand_multiplier=1.0, region=""):
        self.name              = name
        self.base_demand       = base_demand.copy()
        self.demand_std        = demand_std.copy()
        self.return_rate       = return_rate.copy()
        self._base_return_rate = return_rate.copy()
        self.demand_multiplier = demand_multiplier
        self.region            = region

    def generate_demand(self):
        return {
            fp: max(0.0, random.gauss(
                self.base_demand.get(fp, 0) * self.demand_multiplier,
                self.demand_std.get(fp, 0)
            ))
            for fp in FINAL_PRODUCTS
        }

    def generate_returns(self, received):
        return {
            f"rp{i+1}": received.get(fp, 0) * self.return_rate.get(fp, 0)
            for i, fp in enumerate(FINAL_PRODUCTS)
        }

    def disrupt_demand(self, multiplier):
        self.demand_multiplier = multiplier

    def restore_demand(self):
        self.demand_multiplier = 1.0

    def disrupt_returns(self, factor):
        self.return_rate = {fp: r * factor for fp, r in self._base_return_rate.items()}

    def restore_returns(self):
        self.return_rate = self._base_return_rate.copy()

    def __repr__(self):
        return f"MarketNode({self.name}, region={self.region})"
