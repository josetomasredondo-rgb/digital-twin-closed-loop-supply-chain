import pandas as pd

# =============================================================
# MATERIAL & PRODUCT TYPES
# =============================================================

RAW_MATERIALS  = ["RM_1", "RM_2"]
FINAL_PRODUCTS = ["FP_A", "FP_B"]


# =============================================================
# TECHNOLOGY DEFINITIONS
# =============================================================

TECHNOLOGIES = {
    "TECH_P1": {"type": "production",      "input": "RM_1", "output": "FP_A", "input_rate": 1.2, "capacity": 60},
    "TECH_P2": {"type": "production",      "input": "RM_2", "output": "FP_B", "input_rate": 1.5, "capacity": 50},
    "TECH_R1": {"type": "remanufacturing", "input": "FP_A", "output": "FP_A", "input_rate": 1.1, "capacity": 30},
    "TECH_R2": {"type": "remanufacturing", "input": "FP_B", "output": "FP_B", "input_rate": 1.3, "capacity": 25},
}


# =============================================================
# COST & EMISSIONS PARAMETERS  (placeholders — replace with real data)
# =============================================================

PRODUCTION_COST = {"TECH_P1": 5.0, "TECH_P2": 6.0, "TECH_R1": 3.0, "TECH_R2": 3.5}
PRODUCTION_EMISSIONS = {"TECH_P1": 2.0, "TECH_P2": 2.5, "TECH_R1": 0.8, "TECH_R2": 1.0}
TRANSPORT_COST_PER_KM = 0.02
TRANSPORT_EMISSIONS_PER_KM = 0.001
HOLDING_COST = {"supplier": 0.5, "factory_rm": 0.8, "factory_fp": 1.0, "warehouse": 1.2}
UNMET_PENALTY = 10000.0


# =============================================================
# DISTANCE TABLE (km)
# =============================================================

DISTANCE_TABLE = pd.DataFrame(
    {
        "Supplier_A":  [  0, 310,  80, 200,   0,   0,   0,   0,   0,   0],
        "Supplier_B":  [310,   0, 200,  90,   0,   0,   0,   0,   0,   0],
        "Factory_1":   [ 80, 200,   0, 320, 150, 200, 340,   0,   0,   0],
        "Factory_2":   [200,  90, 320,   0, 210, 180, 150,   0,   0,   0],
        "Warehouse_1": [  0,   0, 150, 210,   0,  90, 250, 120, 300, 410],
        "Warehouse_2": [  0,   0, 200, 180,  90,   0, 170, 310, 140, 280],
        "Warehouse_3": [  0,   0, 340, 150, 250, 170,   0, 430, 260, 100],
        "Market_A":    [  0,   0,   0,   0, 120, 310, 430,   0, 180, 300],
        "Market_B":    [  0,   0,   0,   0, 300, 140, 260, 180,   0, 210],
        "Market_C":    [  0,   0,   0,   0, 410, 280, 100, 300, 210,   0],
    },
    index=["Supplier_A", "Supplier_B", "Factory_1", "Factory_2",
           "Warehouse_1", "Warehouse_2", "Warehouse_3",
           "Market_A", "Market_B", "Market_C"]
)
