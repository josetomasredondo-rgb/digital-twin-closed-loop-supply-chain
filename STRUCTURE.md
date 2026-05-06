## Supply Chain Simulation - Project Structure

After reorganization, the project now has a clear separation between two implementations:

### Structure

```
src/
├── __init__.py
├── basic/              # Simple closed-loop simulation (baseline implementation)
│   ├── __init__.py
│   ├── main.py         # Entry point for basic simulation
│   ├── simulator.py    # Core simulation engine
│   ├── nodes.py        # Supply chain nodes (Supplier, Factory, Warehouse, Market)
│   ├── data.py         # Configuration and constants
│   └── visualization.py # Result plotting
│
└── decision_support/   # Advanced version with scenarios & optimization
    ├── __init__.py
    ├── main.py         # Entry point for decision support system
    ├── simulator.py    # Simulation with scenario support
    ├── nodes.py        # Enhanced supply chain nodes
    ├── optimizer.py    # Supply chain optimization (PuLP)
    ├── constants.py    # Configuration and constants
    └── visualization.py # Advanced result visualization & comparison
```

### Running Each Version

**Basic Version:**
```bash
python -m src.basic.main
```

**Decision Support System (with optimization & scenarios):**
```bash
python -m src.decision_support.main
```

### Key Differences

| Aspect | Basic | Decision Support |
|--------|-------|-------------------|
| Complexity | Simple heuristic flow | Complex with optimization |
| Scenarios | Single run | Multiple scenarios with comparison |
| Optimization | None | PuLP-based linear optimization |
| Output | Single CSV + plots | Multiple CSVs per scenario + comparison plots |

### Importing in Other Code

```python
# Use basic version
from src.basic import ClosedLoopSimulator, plot_results

# Use decision support version
from src.decision_support import ClosedLoopSimulator, get_scenarios, plot_scenario_comparison
```

### Migration Notes

- All files from `tests/decision_support_*` have been moved to `src/decision_support/` with cleaner names
- All imports have been updated to use relative imports within each package
- The original `tests/` directory can now be used for unit tests instead of example code
