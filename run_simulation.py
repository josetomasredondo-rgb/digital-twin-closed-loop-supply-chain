#!/usr/bin/env python3
"""
Simple runner script for the Digital Twin Closed-Loop Supply Chain simulation.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now import and run the main function
from decision_support.main import main

if __name__ == "__main__":
    main()