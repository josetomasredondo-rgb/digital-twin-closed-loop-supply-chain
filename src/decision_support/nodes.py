import random
from .constants import FINAL_PRODUCTS, RECOVERED_PRODUCTS, TECHNOLOGIES


class SupplierNode:
    def __init__(self, name, inventory, capacity, restock_rate):
        self.name               = name
        self.inventory          = inventory.copy()
        self.capacity           = capacity.copy()
        self.restock_rate       = restock_rate.copy()
        self._base_restock_rate = restock_rate.copy()

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

    def disrupt(self):
        self.restock_rate = {rm: 0 for rm in self.restock_rate}

    def restore(self):
        self.restock_rate = self._base_restock_rate.copy()


class FactoryNode:
    def __init__(self, name, rm_inventory, fp_inventory,
                 rm_capacity, fp_capacity, technology_ids,
                 employees=0, region=""):
        self.name         = name
        self.rm_inventory = rm_inventory.copy()
        self.fp_inventory = fp_inventory.copy()
        self.rm_capacity  = rm_capacity.copy()
        self.fp_capacity  = fp_capacity.copy()
        self.technologies = {tid: TECHNOLOGIES[tid] for tid in technology_ids}
        self.rp_inventory = {rp: 0.0 for rp in RECOVERED_PRODUCTS}
        self.employees    = employees
        self.region       = region
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
        tech     = self.technologies[tech_id]
        quantity = max(0.0, quantity)
        fp_space = self.fp_capacity.get(tech["output"], 0) - self.fp_inventory.get(tech["output"], 0)
        if tech["type"] == "production":
            # All raw materials are consumed simultaneously; most constrained RM limits output
            max_out = min(quantity, tech["capacity"], fp_space)
            for rm, rate in tech["inputs"].items():
                if rate > 0:
                    max_out = min(max_out, self.rm_inventory.get(rm, 0.0) / rate)
            output = max(0.0, max_out)
            for rm, rate in tech["inputs"].items():
                self.rm_inventory[rm] = self.rm_inventory.get(rm, 0.0) - output * rate
        else:
            rp_avail = self.rp_inventory.get(tech["input"], 0)
            max_out  = min(quantity,
                           rp_avail / tech["input_rate"],
                           tech["capacity"],
                           fp_space)
            output   = max(0.0, max_out)
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

    def disrupt(self):
        self.active = False

    def restore(self):
        self.active = True


class WarehouseNode:
    def __init__(self, name, inventory, capacity, employees=0, region=""):
        self.name      = name
        self.inventory = inventory.copy()
        self.capacity  = capacity.copy()
        self.employees = employees
        self.region    = region

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
        self.name                    = name
        self.base_demand             = base_demand.copy()
        self.demand_std              = demand_std.copy()
        self.return_rate             = return_rate.copy()
        self._base_return_rate       = return_rate.copy()
        self.demand_multiplier       = demand_multiplier
        self._base_demand_multiplier = demand_multiplier

    def generate_demand(self):
        return {
            fp: max(0.0, random.gauss(
                self.base_demand.get(fp, 0) * self.demand_multiplier,
                self.demand_std.get(fp, 0)
            ))
            for fp in FINAL_PRODUCTS
        }

    def generate_returns(self, received):
        # fp delivered → rp returned: fp1→rp1, fp2→rp2, fp3→rp3
        return {
            rp: received.get(fp, 0) * self.return_rate.get(fp, 0)
            for fp, rp in zip(FINAL_PRODUCTS, RECOVERED_PRODUCTS)
        }

    def disrupt(self, demand_multiplier=None, return_rate_factor=None):
        if demand_multiplier is not None:
            self.demand_multiplier = demand_multiplier
        if return_rate_factor is not None:
            self.return_rate = {fp: r * return_rate_factor
                                for fp, r in self._base_return_rate.items()}

    def restore(self):
        self.demand_multiplier = self._base_demand_multiplier
        self.return_rate       = self._base_return_rate.copy()
