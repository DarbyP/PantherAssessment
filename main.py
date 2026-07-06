#!/usr/bin/env python3
"""
Panther Assessment
Main application entry point
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.ui.main_window import main

if __name__ == "__main__":
    main()
