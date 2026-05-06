import pulp
from .constants import (
    DISTANCE_TABLE,
    FINAL_PRODUCTS,
    HOLDING_COST,
    PRODUCTION_COST,
    PRODUCTION_EMISSIONS,
    RAW_MATERIALS,
    TRANSPORT_COST_PER_KM,
    TRANSPORT_EMISSIONS_PER_KM,
    UNMET_PENALTY,
)


class SupplyChainOptimizer:
    """
    Solves a linear program each period to recommend:
      - production and remanufacturing quantities
      - factory -> warehouse shipments
      - warehouse -> market shipments

    The objective minimizes unmet demand penalty plus normalized cost and emissions.
    """

    def __init__(self):
        pass

    def optimize(self, factories, warehouses, markets, suppliers):
        prob = pulp.LpProblem("SC_Optimization", pulp.LpMinimize)

        prod = {
            (f.name, tid): pulp.LpVariable(f"prod_{f.name}_{tid}", lowBound=0)
            for f in factories if f.active
            for tid in f.technologies
        }

        ship_fw = {
            (f.name, w.name, fp): pulp.LpVariable(f"ship_fw_{f.name}_{w.name}_{fp}", lowBound=0)
            for f in factories if f.active
            for w in warehouses
            for fp in FINAL_PRODUCTS
        }

        ship_wm = {
            (w.name, m.name, fp): pulp.LpVariable(f"ship_wm_{w.name}_{m.name}_{fp}", lowBound=0)
            for w in warehouses
            for m in markets
            for fp in FINAL_PRODUCTS
        }

        demand_samples = {m.name: m.generate_demand() for m in markets}
        unmet = {
            (m.name, fp): pulp.LpVariable(f"unmet_{m.name}_{fp}", lowBound=0)
            for m in markets
            for fp in FINAL_PRODUCTS
        }

        for f in factories:
            if not f.active:
                continue
            for tid, tech in f.technologies.items():
                prob += prod[(f.name, tid)] <= tech["capacity"], f"cap_{f.name}_{tid}"

        for f in factories:
            if not f.active:
                continue
            for rm in RAW_MATERIALS:
                rm_used = pulp.lpSum(
                    prod[(f.name, tid)] * tech["input_rate"]
                    for tid, tech in f.technologies.items()
                    if tech["type"] == "production" and tech["input"] == rm
                )
                prob += rm_used <= f.rm_inventory.get(rm, 0), f"rm_{f.name}_{rm}"

        for f in factories:
            if not f.active:
                continue
            for fp in FINAL_PRODUCTS:
                rp_used = pulp.lpSum(
                    prod[(f.name, tid)] * tech["input_rate"]
                    for tid, tech in f.technologies.items()
                    if tech["type"] == "remanufacturing" and tech["input"] == fp
                )
                prob += rp_used <= f.rp_inventory.get(fp, 0), f"rp_{f.name}_{fp}"

        for f in factories:
            if not f.active:
                continue
            for fp in FINAL_PRODUCTS:
                produced_fp = pulp.lpSum(
                    prod[(f.name, tid)]
                    for tid, tech in f.technologies.items()
                    if tech["output"] == fp
                )
                shipped_out = pulp.lpSum(
                    ship_fw[(f.name, w.name, fp)] for w in warehouses
                )
                prob += (f.fp_inventory.get(fp, 0) + produced_fp >= shipped_out,
                         f"factory_bal_{f.name}_{fp}")

        for w in warehouses:
            for fp in FINAL_PRODUCTS:
                received_fw = pulp.lpSum(
                    ship_fw[(f.name, w.name, fp)] for f in factories if f.active
                )
                shipped_wm = pulp.lpSum(
                    ship_wm[(w.name, m.name, fp)] for m in markets
                )
                prob += (w.inventory.get(fp, 0) + received_fw >= shipped_wm,
                         f"wh_bal_{w.name}_{fp}")

        for w in warehouses:
            for fp in FINAL_PRODUCTS:
                received_fw = pulp.lpSum(
                    ship_fw[(f.name, w.name, fp)] for f in factories if f.active
                )
                prob += (w.inventory.get(fp, 0) + received_fw <= w.capacity.get(fp, 0),
                         f"wh_cap_{w.name}_{fp}")

        for m in markets:
            for fp in FINAL_PRODUCTS:
                shipped_to_m = pulp.lpSum(
                    ship_wm[(w.name, m.name, fp)] for w in warehouses
                )
                prob += (shipped_to_m + unmet[(m.name, fp)] >= demand_samples[m.name][fp],
                         f"demand_{m.name}_{fp}")

        obj_unmet = pulp.lpSum(
            unmet[(m.name, fp)] * UNMET_PENALTY
            for m in markets for fp in FINAL_PRODUCTS
        )

        obj_cost = (
            pulp.lpSum(
                prod[(f.name, tid)] * PRODUCTION_COST[tid]
                for f in factories if f.active
                for tid in f.technologies
            )
            + pulp.lpSum(
                ship_fw[(f.name, w.name, fp)]
                * DISTANCE_TABLE.loc[f.name, w.name]
                * TRANSPORT_COST_PER_KM
                for f in factories if f.active
                for w in warehouses
                for fp in FINAL_PRODUCTS
            )
            + pulp.lpSum(
                ship_wm[(w.name, m.name, fp)]
                * DISTANCE_TABLE.loc[w.name, m.name]
                * TRANSPORT_COST_PER_KM
                for w in warehouses
                for m in markets
                for fp in FINAL_PRODUCTS
            )
            + pulp.lpSum(
                ship_fw[(f.name, w.name, fp)] * HOLDING_COST["warehouse"]
                for f in factories if f.active
                for w in warehouses
                for fp in FINAL_PRODUCTS
            )
        )

        obj_emissions = (
            pulp.lpSum(
                prod[(f.name, tid)] * PRODUCTION_EMISSIONS[tid]
                for f in factories if f.active
                for tid in f.technologies
            )
            + pulp.lpSum(
                ship_fw[(f.name, w.name, fp)]
                * DISTANCE_TABLE.loc[f.name, w.name]
                * TRANSPORT_EMISSIONS_PER_KM
                for f in factories if f.active
                for w in warehouses
                for fp in FINAL_PRODUCTS
            )
            + pulp.lpSum(
                ship_wm[(w.name, m.name, fp)]
                * DISTANCE_TABLE.loc[w.name, m.name]
                * TRANSPORT_EMISSIONS_PER_KM
                for w in warehouses
                for m in markets
                for fp in FINAL_PRODUCTS
            )
        )

        scale_cost      = 1000.0
        scale_emissions = 500.0

        prob += (
            obj_unmet
          + obj_cost      / scale_cost
          + obj_emissions / scale_emissions
        )

        prob.solve(pulp.PULP_CBC_CMD(msg=0))

        prod_plan = {k: max(0.0, v.varValue or 0.0) for k, v in prod.items()}
        ship_fw_plan = {k: max(0.0, v.varValue or 0.0) for k, v in ship_fw.items()}
        ship_wm_plan = {k: max(0.0, v.varValue or 0.0) for k, v in ship_wm.items()}

        obj_values = {
            "status":     pulp.LpStatus[prob.status],
            "unmet":      sum(max(0.0, v.varValue or 0.0) for v in unmet.values()),
            "cost":       pulp.value(obj_cost)      or 0.0,
            "emissions":  pulp.value(obj_emissions) or 0.0,
            "demand":     {m.name: demand_samples[m.name] for m in markets},
        }

        return prod_plan, ship_fw_plan, ship_wm_plan, obj_values
