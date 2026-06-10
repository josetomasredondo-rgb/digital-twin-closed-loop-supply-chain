import pandas as pd

# =============================================================
# MATERIAL & PRODUCT TYPES
# =============================================================

RAW_MATERIALS      = ["rm1", "rm2", "rm3", "rm4"]
FINAL_PRODUCTS     = ["fp1", "fp2", "fp3"]
RECOVERED_PRODUCTS = ["rp1", "rp2", "rp3"]


# =============================================================
# TECHNOLOGY DEFINITIONS
# =============================================================
#
# Production:      'inputs' maps each raw material to units consumed per unit of fp output.
#                  All 4 raw materials are consumed simultaneously in fixed ratios.
# Remanufacturing: 'input' is the recovered product consumed; 'input_rate' is units of rp
#                  consumed per unit of fp output (e.g. re1: 2 rp1 → 1 fp1).
# pr4 is an alternative technology that can be allocated to produce fp1 OR fp2;
# represented as two LP variants (pr4_fp1, pr4_fp2) so the optimizer can choose.

TECHNOLOGIES = {
    # --- Production ---
    "pr1":     {"type": "production", "inputs": {"rm1": 0.25,  "rm2": 0.30,  "rm3": 0.15,  "rm4": 0.30},  "output": "fp1", "capacity": 60},
    "pr4_fp1": {"type": "production", "inputs": {"rm1": 0.45,  "rm2": 0.30,  "rm3": 0.025, "rm4": 0.225}, "output": "fp1", "capacity": 50},
    "pr2":     {"type": "production", "inputs": {"rm1": 0.255, "rm2": 0.355, "rm3": 0.14,  "rm4": 0.25},  "output": "fp2", "capacity": 55},
    "pr4_fp2": {"type": "production", "inputs": {"rm1": 0.32,  "rm2": 0.42,  "rm3": 0.11,  "rm4": 0.15},  "output": "fp2", "capacity": 50},
    "pr3":     {"type": "production", "inputs": {"rm1": 0.20,  "rm2": 0.25,  "rm3": 0.25,  "rm4": 0.30},  "output": "fp3", "capacity": 55},
    # --- Remanufacturing: rp → fp ---
    "re1":     {"type": "remanufacturing", "input": "rp1", "input_rate": 2, "output": "fp1", "capacity": 30},
    "re2":     {"type": "remanufacturing", "input": "rp2", "input_rate": 3, "output": "fp2", "capacity": 25},
    "re3":     {"type": "remanufacturing", "input": "rp3", "input_rate": 2, "output": "fp3", "capacity": 28},
}


# =============================================================
# COST & EMISSIONS PARAMETERS  (placeholders — replace with real data)
# =============================================================

PRODUCTION_COST = {
    "pr1": 5.0, "pr4_fp1": 5.5, "pr2": 6.0, "pr4_fp2": 6.5, "pr3": 5.5,
    "re1": 3.0, "re2":     3.5, "re3": 3.2,
}
PRODUCTION_EMISSIONS = {
    "pr1": 2.0, "pr4_fp1": 2.2, "pr2": 2.5, "pr4_fp2": 2.6, "pr3": 2.2,
    "re1": 0.8, "re2":     1.0, "re3": 0.9,
}
TRANSPORT_COST_PER_KM      = 0.02
TRANSPORT_EMISSIONS_PER_KM = 0.001
HOLDING_COST  = {"supplier": 0.5, "factory_rm": 0.8, "factory_fp": 1.0, "warehouse": 1.2}
UNMET_PENALTY = 10000.0

# Social pillar: GDP per capita (€) and unemployment rate by region.
# Real-city values from thesis data; generic placeholders for nodes not yet renamed.
SOCIAL_DATA = {
    "Lyon":      {"gdp_per_capita": 49_492, "unemployment_rate": 0.080},
    "Bremen":    {"gdp_per_capita": 56_956, "unemployment_rate": 0.038},
    "Galway":    {"gdp_per_capita": 99_239, "unemployment_rate": 0.056},
    "Madrid":    {"gdp_per_capita": 41_546, "unemployment_rate": 0.155},
    "Lisbon":    {"gdp_per_capita": 36_079, "unemployment_rate": 0.068},
    "Vancouver": {"gdp_per_capita": 51_713, "unemployment_rate": 0.055},
    # Generic regions — to be replaced when nodes are renamed to real locations
    "North":    {"gdp_per_capita": 45_000, "unemployment_rate": 0.070},
    "Central":  {"gdp_per_capita": 45_000, "unemployment_rate": 0.070},
    "South":    {"gdp_per_capita": 40_000, "unemployment_rate": 0.090},
    "East":     {"gdp_per_capita": 42_000, "unemployment_rate": 0.080},
    "West":     {"gdp_per_capita": 43_000, "unemployment_rate": 0.075},
}

# Cost and emissions multipliers relative to truck baseline.
# Applied to all outbound shipments when a strategy uses a non-truck mode.
TRANSPORT_MODE_MULTIPLIERS = {
    "truck": {"cost": 1.00, "emissions": 1.00},
    "air":   {"cost": 4.00, "emissions": 5.70},
    "sea":   {"cost": 0.75, "emissions": 0.33},
}


# =============================================================
# DISTANCE TABLE (km)  — node names are placeholders pending rename to real locations
# =============================================================

DISTANCE_TABLE = pd.DataFrame(
    {
        "Supplier_A":  [  0, 310,  80, 200, 150,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        "Supplier_B":  [310,   0, 200,  90, 180,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        "Supplier_C":  [150, 180, 120, 160,  90,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        "Factory_1":   [ 80, 200, 120,   0, 320, 150, 200, 340, 280, 220,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        "Factory_2":   [200,  90, 160, 320,   0, 210, 180, 150, 190, 240,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        "Factory_3":   [120, 160,  90, 280, 190, 130, 160, 180, 120, 170,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        "Warehouse_1": [  0,   0,   0, 150, 210, 130,  90, 250, 180, 140, 120, 300, 410, 180, 210, 160, 190, 220, 250, 280, 320, 350, 380],
        "Warehouse_2": [  0,   0,   0, 200, 180, 160,   0, 170, 140, 120, 310, 140, 280, 160, 180, 140, 170, 200, 230, 260, 290, 320, 350],
        "Warehouse_3": [  0,   0,   0, 340, 150, 180, 170,   0, 120, 100, 430, 260, 100, 140, 160, 120, 150, 180, 210, 240, 270, 300, 330],
        "Warehouse_4": [  0,   0,   0, 280, 190, 140, 140, 120,  80,  90, 350, 180, 120, 100, 120,  80, 110, 140, 170, 200, 230, 260, 290],
        "Warehouse_5": [  0,   0,   0, 220, 240, 120, 120, 100,  90,  60, 380, 200, 140, 120, 140, 100, 130, 160, 190, 220, 250, 280, 310],
        "Market_1":    [  0,   0,   0,   0,   0, 120, 310, 430, 350, 380,   0, 180, 300, 140, 160, 120, 150, 180, 210, 240, 270, 300, 330],
        "Market_2":    [  0,   0,   0,   0,   0, 300, 140, 260, 180, 200, 180,   0, 210, 120, 140, 100, 130, 160, 190, 220, 250, 280, 310],
        "Market_3":    [  0,   0,   0,   0,   0, 410, 280, 100, 120, 140, 300, 210,   0, 160, 180, 140, 170, 200, 230, 260, 290, 320, 350],
        "Market_4":    [  0,   0,   0,   0,   0, 180, 160, 140, 100, 120, 140, 120, 160,  80, 100,  60,  90, 120, 150, 180, 210, 240, 270],
        "Market_5":    [  0,   0,   0,   0,   0, 210, 180, 160, 120, 140, 160, 140, 180, 100,  60,  80, 110, 140, 170, 200, 230, 260, 290],
        "Market_6":    [  0,   0,   0,   0,   0, 160, 140, 120,  80, 100, 120, 100, 140,  60,  80,  40,  70, 100, 130, 160, 190, 220, 250],
        "Airport_North":    [  0,   0,   0,   0,   0, 190, 170, 150, 110, 130, 150, 130, 170,  90, 110,  70,  50,  80, 110, 140, 170, 200, 230],
        "Airport_Central":  [  0,   0,   0,   0,   0, 220, 200, 180, 140, 160, 180, 160, 200, 120, 140, 100,  80,  50,  80, 110, 140, 170, 200],
        "Airport_South":    [  0,   0,   0,   0,   0, 250, 230, 210, 170, 190, 210, 190, 230, 150, 170, 130, 110,  80,  50,  80, 110, 140, 170],
        "Port_West":        [  0,   0,   0,   0,   0, 280, 260, 240, 200, 220, 240, 220, 260, 180, 200, 160, 140, 110,  80,  50,  80, 110, 140],
        "Port_East":        [  0,   0,   0,   0,   0, 320, 300, 280, 240, 260, 280, 260, 300, 220, 240, 200, 180, 150, 120,  90,  50,  80, 110],
        "Port_South":       [  0,   0,   0,   0,   0, 350, 330, 310, 270, 290, 310, 290, 330, 250, 270, 230, 210, 180, 150, 120,  90,  50,  80],
    },
    index=["Supplier_A", "Supplier_B", "Supplier_C",
           "Factory_1", "Factory_2", "Factory_3",
           "Warehouse_1", "Warehouse_2", "Warehouse_3", "Warehouse_4", "Warehouse_5",
           "Market_1", "Market_2", "Market_3", "Market_4", "Market_5", "Market_6",
           "Airport_North", "Airport_Central", "Airport_South",
           "Port_West", "Port_East", "Port_South"]
)
