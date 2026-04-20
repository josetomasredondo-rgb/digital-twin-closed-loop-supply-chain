import random
from tests.decision_support_constants import FINAL_PRODUCTS, TECHNOLOGIES


class SupplierNode:
    def __init__(self, name, inventory, capacity, restock_rate):
        self.name         = name
        self.inventory    = inventory.copy()
        self.capacity     = capacity.copy()
        self.restock_rate = restock_rate.copy()

    def restock(self):
        for rm in self.inventory:
            self.inventory[rm] = min(
                self.capacity[rm],
                self.inventory[rm] + self.restock_rate.get(rm, 0)
            )

    def ship(self, rm_type, quantity):
        available = self.inventory.get(rm_type, 0)
        shipped   = min(max(0.0, quantity), available)
        self.inventory[rm_type] = available - shipped
        return shipped


class FactoryNode:
    def __init__(self, name, rm_inventory, fp_inventory,
                 rm_capacity, fp_capacity, technology_ids):
        self.name         = name
        self.rm_inventory = rm_inventory.copy()
        self.fp_inventory = fp_inventory.copy()
        self.rm_capacity  = rm_capacity.copy()
        self.fp_capacity  = fp_capacity.copy()
        self.technologies = {tid: TECHNOLOGIES[tid] for tid in technology_ids}
        self.rp_inventory = {fp: 0.0 for fp in FINAL_PRODUCTS}
        self.active       = True

    def receive_rm(self, rm_type, quantity):
        space    = self.rm_capacity.get(rm_type, 0) - self.rm_inventory.get(rm_type, 0)
        received = min(max(0.0, quantity), space)
        self.rm_inventory[rm_type] = self.rm_inventory.get(rm_type, 0) + received
        return received

    def receive_rp(self, fp_type, quantity):
        received = max(0.0, quantity)
        self.rp_inventory[fp_type] = self.rp_inventory.get(fp_type, 0) + received
        return received

    def produce(self, tech_id, quantity):
        if not self.active or tech_id not in self.technologies:
            return 0.0
        tech      = self.technologies[tech_id]
        quantity  = max(0.0, quantity)
        fp_space  = self.fp_capacity.get(tech["output"], 0) - self.fp_inventory.get(tech["output"], 0)
        if tech["type"] == "production":
            rm_avail  = self.rm_inventory.get(tech["input"], 0)
            max_out   = min(quantity,
                            rm_avail / tech["input_rate"],
                            tech["capacity"],
                            fp_space)
            output    = max(0.0, max_out)
            self.rm_inventory[tech["input"]]  -= output * tech["input_rate"]
        else:
            rp_avail  = self.rp_inventory.get(tech["input"], 0)
            max_out   = min(quantity,
                            rp_avail / tech["input_rate"],
                            tech["capacity"],
                            fp_space)
            output    = max(0.0, max_out)
            self.rp_inventory[tech["input"]] -= output * tech["input_rate"]
        self.fp_inventory[tech["output"]] = self.fp_inventory.get(tech["output"], 0) + output
        return output

    def ship_fp(self, fp_type, quantity):
        if not self.active:
            return 0.0
        available = self.fp_inventory.get(fp_type, 0)
        shipped   = min(max(0.0, quantity), available)
        self.fp_inventory[fp_type] = available - shipped
        return shipped


class WarehouseNode:
    def __init__(self, name, inventory, capacity):
        self.name      = name
        self.inventory = inventory.copy()
        self.capacity  = capacity.copy()

    def receive(self, fp_type, quantity):
        space    = self.capacity.get(fp_type, 0) - self.inventory.get(fp_type, 0)
        received = min(max(0.0, quantity), space)
        self.inventory[fp_type] = self.inventory.get(fp_type, 0) + received
        return received

    def ship(self, fp_type, quantity):
        available = self.inventory.get(fp_type, 0)
        shipped   = min(max(0.0, quantity), available)
        self.inventory[fp_type] = available - shipped
        return shipped


class MarketNode:
    def __init__(self, name, base_demand, demand_std, return_rate,
                 demand_multiplier=1.0):
        self.name              = name
        self.base_demand       = base_demand.copy()
        self.demand_std        = demand_std.copy()
        self.return_rate       = return_rate.copy()
        self.demand_multiplier = demand_multiplier

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
            fp: received.get(fp, 0) * self.return_rate.get(fp, 0)
            for fp in FINAL_PRODUCTS
        }
