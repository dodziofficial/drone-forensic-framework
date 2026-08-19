"""
Drone Forensic Framework - Main Entry Point
Author: Dodzi Gbordzi
KNUST MSc. Cyber Security and Digital Forensics
"""

import sys
import tkinter as tk
from pathlib import Path

# Add project root to path so imports work from any directory
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    root = tk.Tk()
    from drone_forensics.gui.main_window import DroneForensicGUI
    app = DroneForensicGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()