import random

class SupplyChainSimulator:
    def __init__(self, periods=12):
        self.periods = periods

        self.raw_material_inventory = 200
        self.factory_inventory = 50
        self.warehouse_inventory = 80

        self.supplier_capacity = 100
        self.factory_capacity = 90
        self.reman_capacity = 30
        self.market_base_demand = 70
        self.return_rate = 0.2
        self.recovery_yield = 0.8

    def simulate_period(self, t):
        demand = max(0, int(random.gauss(self.market_base_demand, 10)))

        shipped = min(self.warehouse_inventory, demand)
        unmet = max(0, demand - shipped)
        self.warehouse_inventory -= shipped

        returns = int(shipped * self.return_rate)
        recovered = int(min(returns, self.reman_capacity) * self.recovery_yield)

        production_needed = max(0, 100 - self.warehouse_inventory - recovered)
        new_production = min(production_needed, self.factory_capacity, self.raw_material_inventory)

        self.raw_material_inventory -= new_production
        self.raw_material_inventory += self.supplier_capacity

        self.warehouse_inventory += new_production + recovered

        print(f"Period {t}: Demand={demand}, Shipped={shipped}, Unmet={unmet}, Inventory={self.warehouse_inventory}")

    def run(self):
        for t in range(1, self.periods + 1):
            self.simulate_period(t)


if __name__ == "__main__":
    sim = SupplyChainSimulator()
    sim.run()