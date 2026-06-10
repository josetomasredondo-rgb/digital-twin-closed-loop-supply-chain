"""
constants.py — Supply Chain Parameters for the Digital Twin DSS

Based on the real case study from Camarneiro (2024):
'Decision-Support Tool for Sustainable Supply Chain Design and Planning:
An Optimization-Simulation Approach', IST Lisboa.
"""

import pandas as pd

# =============================================================================
# MATERIAL & PRODUCT TYPES
# =============================================================================

RAW_MATERIALS      = ["rm1", "rm2", "rm3", "rm4"]
FINAL_PRODUCTS     = ["fp1", "fp2", "fp3"]
RECOVERED_PRODUCTS = ["rp1", "rp2", "rp3"]

# =============================================================================
# TECHNOLOGY DEFINITIONS
# =============================================================================

TECHNOLOGIES = {
    "pr1": {"type": "production",      "input": "rm1", "output": "fp1", "input_rate": 1.20, "capacity": 7_500_000},
    "pr2": {"type": "production",      "input": "rm2", "output": "fp2", "input_rate": 1.50, "capacity": 5_400_000},
    "pr3": {"type": "production",      "input": "rm2", "output": "fp3", "input_rate": 1.30, "capacity": 3_780_000},
    "pr4": {"type": "production",      "input": "rm1", "output": "fp1", "input_rate": 1.40, "capacity": 6_480_000},
    "re1": {"type": "remanufacturing", "input": "rp1", "output": "fp1", "input_rate": 2.0,  "capacity": 3_000_000},
    "re2": {"type": "remanufacturing", "input": "rp2", "output": "fp2", "input_rate": 3.0,  "capacity": 1_500_000},
    "re3": {"type": "remanufacturing", "input": "rp3", "output": "fp3", "input_rate": 2.0,  "capacity": 1_200_000},
}

# =============================================================================
# FACTORY TECHNOLOGY ASSIGNMENTS — Case F: Bremen has NO remanufacturing
# =============================================================================

FACTORY_TECHNOLOGIES = {
    "Factory_Lyon":    ["pr1", "pr3", "pr4", "re1", "re2", "re3"],
    "Factory_Bremen":  ["pr1", "pr2", "pr4"],   # no remanufacturing, no fp3
    "Factory_Galway":  ["pr1", "pr2", "pr3", "re1", "re2", "re3"],
}

# =============================================================================
# COST PARAMETERS (€/unit)
# =============================================================================

PRODUCTION_COST = {
    "pr1": 0.1802, "pr2": 0.2754, "pr3": 0.1928, "pr4": 0.2270,
    "re1": 0.0986, "re2": 0.1139, "re3": 0.1139,
}

# =============================================================================
# EMISSIONS PARAMETERS (kg CO2e/unit)
# =============================================================================

PRODUCTION_EMISSIONS = {
    "pr1": 0.542, "pr2": 0.596, "pr3": 0.493, "pr4": 0.379,
    "re1": 0.136, "re2": 0.119, "re3": 0.123,
}

# =============================================================================
# TRANSPORT PARAMETERS
# =============================================================================

# Truck: (fuel 15L/100km × 1.35€/L + 0.35€/km maintenance) × 2 round trip / 45000 units/truck
TRUCK_COST_PER_UNIT_PER_KM = (15 / 100 * 1.35 + 0.35) * 2 / 45_000  # ≈ 2.46e-5 €/unit/km

# Air: outsourced rate per kg.km
AIR_COST_PER_KM = 2e-7             # €/kg.km

# Sea: flat handling fee at hub terminal (loading/unloading only)
SEA_HANDLING_COST_PER_UNIT = 0.015  # €/unit

# Transport emissions per kg.km — CC category, EPS 2015 methodology
TRANSPORT_EMISSIONS_PER_KM = {
    "truck": 6.03e-6,   # kg CO2/kg.km
    "air":   3.88e-6,   # kg CO2/kg.km
    "sea":   1.58e-8,   # kg CO2/kg.km
}

# --- FIX: aliases expected by optimizer.py ---
# optimizer.py imports TRANSPORT_COST_PER_KM (dict keyed by mode)
TRANSPORT_COST_PER_KM = {
    "truck": TRUCK_COST_PER_UNIT_PER_KM,
    "air":   AIR_COST_PER_KM,
    "sea":   SEA_HANDLING_COST_PER_UNIT,
}

# Transport mode multipliers relative to truck baseline
TRANSPORT_MODE_MULTIPLIERS = {
    "truck": {"cost": 1.00, "emissions": 1.00},
    "air":   {"cost": 4.00, "emissions": 5.70},
    "sea":   {"cost": 0.75, "emissions": 0.33},
}

# Transport capacities (units per trip)
TRANSPORT_CAPACITY = {
    "truck": 45_000,
    "air":   250_000,
    "sea":   450_000,
}

# Product weights (kg per unit)
PRODUCT_WEIGHT = {
    "fp1": 0.4,
    "fp2": 0.5,
    "fp3": 0.7,
}

HOLDING_COST = {
    "fp1": 0.015,
    "fp2": 0.015,
    "fp3": 0.015,
    # FIX: optimizer.py references HOLDING_COST["warehouse"] — add it
    "warehouse": 0.015,
}

# =============================================================================
# SOCIAL PILLAR DATA
# =============================================================================

SOCIAL_DATA = {
    "Lyon":      {"gdp_per_capita": 49_492, "unemployment_rate": 0.080},
    "Bremen":    {"gdp_per_capita": 56_956, "unemployment_rate": 0.038},
    "Galway":    {"gdp_per_capita": 99_239, "unemployment_rate": 0.056},
    "Madrid":    {"gdp_per_capita": 41_546, "unemployment_rate": 0.155},
    "Lisbon":    {"gdp_per_capita": 36_079, "unemployment_rate": 0.068},
    "Vancouver": {"gdp_per_capita": 51_713, "unemployment_rate": 0.055},
    "Paris":     {"gdp_per_capita": 49_492, "unemployment_rate": 0.080},
    "Hamburg":   {"gdp_per_capita": 56_956, "unemployment_rate": 0.038},
    "Barcelona": {"gdp_per_capita": 41_546, "unemployment_rate": 0.155},
}

# =============================================================================
# DEMAND & RETURN PARAMETERS
# =============================================================================

UNMET_PENALTY = 10_000.0

MARKET_DEMAND = {
    "Market_Lyon":      {"fp1": 2_482_659, "fp2": 1_489_595, "fp3": 1_093_046},
    "Market_Bremen":    {"fp1": 1_545_827, "fp2":   927_496, "fp3": 1_130_509},
    "Market_Vancouver": {"fp1":   983_965, "fp2":   590_379, "fp3":   744_215},
    "Market_Galway":    {"fp1": 1_055_317, "fp2":   633_190, "fp3":   594_222},
    "Market_Lisbon":    {"fp1":   975_318, "fp2":   585_191, "fp3":   767_007},
    "Market_Madrid":    {"fp1":   794_417, "fp2":   476_650, "fp3": 1_001_307},
}

PERIODS = 48
MARKET_DEMAND_PER_PERIOD = {
    market: {fp: qty / PERIODS for fp, qty in demand.items()}
    for market, demand in MARKET_DEMAND.items()
}

DEMAND_STD_FACTOR = 0.10

RETURN_RATES = {
    "fp1": 0.10,
    "fp2": 0.20,
    "fp3": 0.15,
}

# =============================================================================
# DISTANCE TABLE (km) — 19 nodes
# =============================================================================

_NODES = [
    "Supplier_Lyon", "Supplier_Bremen", "Supplier_Galway",
    "Factory_Lyon", "Factory_Bremen", "Factory_Galway",
    "Warehouse_Lyon",
    "Market_Lyon", "Market_Bremen", "Market_Vancouver",
    "Market_Galway", "Market_Lisbon", "Market_Madrid",
    "Port_Hamburg", "Port_Barcelona", "Port_Vancouver",
    "Airport_Madrid", "Airport_Paris", "Airport_Vancouver",
]

_DIST = [
  [    0,  900, 1800,    5,  900, 1800,    5,    5,  900,    0, 1800, 1350,  800,  900,  500,    0,  800,  470,    0],
  [  900,    0, 1700,  900,    5, 1700,  900,  900,    5,    0, 1700, 2200, 1800,  120, 1800,    0, 1800,  900,    0],
  [ 1800, 1700,    0, 1800, 1700,    5, 1800, 1800, 1700,    0,    5,    0,    0,    0,    0,    0,    0,    0,    0],
  [    5,  900, 1800,    0,  900, 1800,    5,    5,  900,    0, 1800, 1350,  800,  900,  500,    0,  800,  470,    0],
  [  900,    5, 1700,  900,    0, 1700,  900,  900,    5,    0, 1700, 2200, 1800,  120, 1800,    0, 1800,  900,    0],
  [ 1800, 1700,    5, 1800, 1700,    0, 1800, 1800, 1700,    0,    5,    0,    0,    0,    0,    0,    0,    0,    0],
  [    5,  900, 1800,    5,  900, 1800,    0,    5,  900,    0, 1800, 1350,  800,  900,  500,    0,  800,  470,    0],
  [    5,  900, 1800,    5,  900, 1800,    5,    0,  900,    0, 1800, 1350,  800,  900,  500,    0,  800,  470,    0],
  [  900,    5, 1700,  900,    5, 1700,  900,  900,    0,    0, 1700, 2200, 1800,  120, 1800,    0, 1800,  900,    0],
  [    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,   15,    0,    0,   15],
  [ 1800, 1700,    5, 1800, 1700,    5, 1800, 1800, 1700,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0],
  [ 1350, 2200,    0, 1350, 2200,    0, 1350, 1350, 2200,    0,    0,    0,  630,    0,    0,    0,    0,    0,    0],
  [  800, 1800,    0,  800, 1800,    0,  800,  800, 1800,    0,    0,  630,    0,    0,  500,    0,    5,    0,    0],
  [  900,  120,    0,  900,  120,    0,  900,  900,  120,    0,    0,    0,    0,    0,    0,11800,    0,  900,    0],
  [  500, 1800,    0,  500, 1800,    0,  500,  500, 1800,    0,    0,    0,  500,    0,    0,11600,  500,    0,    0],
  [    0,    0,    0,    0,    0,    0,    0,    0,    0,   15,    0,    0,    0,11800,11600,    0,    0,    0,   15],
  [  800, 1800,    0,  800, 1800,    0,  800,  800, 1800,    0,    0,    0,    5,    0,  500,    0,    0, 1250,    0],
  [  470,  900,    0,  470,  900,    0,  470,  470,  900,    0,    0,    0,    0,  900,    0,    0, 1250,    0, 8500],
  [    0,    0,    0,    0,    0,    0,    0,    0,    0,   15,    0,    0,    0,    0,    0,   15,    0, 8500,    0],
]

DISTANCE_TABLE = pd.DataFrame(_DIST, index=_NODES, columns=_NODES)
