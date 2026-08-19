"""
I created this test script to verify Drone Forensic Framework installation
Run: python test_framework.py
"""

import sys
import os

def test_imports():
    """Test that all required packages are installed"""
    print("\n[1] Testing Python Package Imports...")
    print("-" * 40)
    
    try:
        import cv2
        print(f"  ✅ OpenCV: {cv2.__version__}")
    except ImportError:
        print("  ❌ OpenCV not installed. Run: pip install opencv-python")
        return False
    
    try:
        import pytesseract
        print(f"  ✅ PyTesseract installed")
    except ImportError:
        print("  ❌ PyTesseract not installed. Run: pip install pytesseract")
        return False
    
    try:
        import numpy as np
        print(f"  ✅ NumPy: {np.__version__}")
    except ImportError:
        print("  ❌ NumPy not installed. Run: pip install numpy")
        return False
    
    try:
        import pandas as pd
        print(f"  ✅ Pandas: {pd.__version__}")
    except ImportError:
        print("  ❌ Pandas not installed. Run: pip install pandas")
        return False
    
    try:
        from PIL import Image
        print(f"  ✅ Pillow: {Image.__version__}")
    except ImportError:
        print("  ❌ Pillow not installed. Run: pip install pillow")
        return False
    
    print("\n  ✅ All Python packages installed successfully!")
    return True

def test_tesseract():
    """Test Tesseract OCR installation"""
    print("\n[2] Testing Tesseract OCR Installation...")
    print("-" * 40)
    
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"  ✅ Tesseract: {version}")
        return True
    except Exception as e:
        print(f"  ⚠️ Tesseract not found in PATH.")
        print("  Please install Tesseract OCR from:")
        print("  https://github.com/UB-Mannheim/tesseract/wiki")
        return False

def test_framework():
    """Test that the framework modules can be imported"""
    print("\n[3] Testing Framework Modules...")
    print("-" * 40)
    
    try:
        from drone_forensics.core.ocr_extractor import extract_from_screenshots
        print("  ✅ OCR Extractor module loaded")
    except ImportError as e:
        print(f"  ❌ OCR Extractor failed: {e}")
        return False
    
    try:
        from drone_forensics.core.flight_analyzer import ForensicFramework
        print("  ✅ Flight Analyzer module loaded")
    except ImportError as e:
        print(f"  ❌ Flight Analyzer failed: {e}")
        return False
    
    try:
        from drone_forensics.gui.main_window import DroneForensicGUI
        print("  ✅ GUI module loaded")
    except ImportError as e:
        print(f"  ❌ GUI failed: {e}")
        return False
    
    print("\n  ✅ All framework modules loaded successfully!")
    return True

def check_config():
    """Check if config.json exists"""
    print("\n[4] Checking Configuration...")
    print("-" * 40)
    
    if os.path.exists("config.json"):
        print("  ✅ config.json found")
        return True
    else:
        print("  ⚠️ config.json not found (will use defaults)")
        return True

def main():
    print("=" * 60)
    print("  DRONE FORENSIC FRAMEWORK - INSTALLATION TEST")
    print("=" * 60)
    
    success = True
    
    if not test_imports():
        success = False
    
    if not test_tesseract():
        print("\n  ⚠️ Tesseract missing - OCR will not work!")
        success = False
    
    if not test_framework():
        success = False
    
    check_config()
    
    print("\n" + "=" * 60)
    if success:
        print("  ✅ ALL TESTS PASSED!")
        print("\n  To run the framework:")
        print("    python -m drone_forensics.main")
    else:
        print("  ❌ SOME TESTS FAILED")
        print("\n  Please fix the issues above and try again.")
    print("=" * 60)

if __name__ == "__main__":
    main()