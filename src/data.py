# =============================================================
# MATERIAL & PRODUCT TYPES
# Define the names of all raw materials, final products here.
# Add or remove entries to match your real supply chain.
# =============================================================

RAW_MATERIALS   = ["RM_1", "RM_2"]           # types of raw material
FINAL_PRODUCTS  = ["FP_A", "FP_B"]           # types of final product


# =============================================================
# TECHNOLOGY DEFINITIONS
# Each technology is a dict describing:
#   "type"       : "production" (uses RM) or "remanufacturing" (uses RP)
#   "input"      : which RM or FP (as RP) it consumes
#   "output"     : which FP it produces
#   "input_rate" : units of input needed to produce 1 unit of output
#   "capacity"   : max units of OUTPUT this technology can produce per period
#
# Example:
#   TECH_P1 uses 1.2 units of RM_1 to produce 1 unit of FP_A, up to 60 units/period
#   TECH_R1 uses 1.1 units of FP_A (returned as RP) to produce 1 unit of FP_A, up to 30 units/period
# =============================================================

TECHNOLOGIES = {
    "TECH_P1": {"type": "production",       "input": "RM_1", "output": "FP_A", "input_rate": 1.2, "capacity": 60},
    "TECH_P2": {"type": "production",       "input": "RM_2", "output": "FP_B", "input_rate": 1.5, "capacity": 50},
    "TECH_R1": {"type": "remanufacturing",  "input": "FP_A", "output": "FP_A", "input_rate": 1.1, "capacity": 30},
    "TECH_R2": {"type": "remanufacturing",  "input": "FP_B", "output": "FP_B", "input_rate": 1.3, "capacity": 25},
}


# =============================================================
# DISTANCE TABLE (km)
# Stores distances between every pair of nodes.
# Not used in simulation logic yet — reserved for future
# transport cost and emissions calculations.
# Rows = origin node, Columns = destination node.
# =============================================================

import pandas as pd

DISTANCE_TABLE = pd.DataFrame(
    {
    #                   S_A   S_B    F1    F2    W1    W2    W3    M_A   M_B   M_C
        "Supplier_A":  [   0, 310,   80,  200,    0,    0,    0,    0,    0,    0],
        "Supplier_B":  [ 310,   0,  200,   90,    0,    0,    0,    0,    0,    0],
        "Factory_1":   [  80, 200,    0,  320,  150,  200,  340,    0,    0,    0],
        "Factory_2":   [ 200,  90,  320,    0,  210,  180,  150,    0,    0,    0],
        "Warehouse_1": [   0,   0,  150,  210,    0,   90,  250,  120,  300,  410],
        "Warehouse_2": [   0,   0,  200,  180,   90,    0,  170,  310,  140,  280],
        "Warehouse_3": [   0,   0,  340,  150,  250,  170,    0,  430,  260,  100],
        "Market_A":    [   0,   0,    0,    0,  120,  310,  430,    0,  180,  300],
        "Market_B":    [   0,   0,    0,    0,  300,  140,  260,  180,    0,  210],
        "Market_C":    [   0,   0,    0,    0,  410,  280,  100,  300,  210,    0],
    },
    index=["Supplier_A", "Supplier_B", "Factory_1", "Factory_2",
           "Warehouse_1", "Warehouse_2", "Warehouse_3", "Market_A", "Market_B", "Market_C"]
)