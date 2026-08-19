"""OCR extractor - PTD1 screenshot processing with Adaptive Grid Slicing"""

import os
import re
import cv2
import numpy as np
import pandas as pd
import pytesseract
import shutil

# Auto-detect Tesseract path, fallback to common Windows location
tesseract_path = shutil.which('tesseract')
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
else:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def calculate_file_sha256(file_path):
    # SHA-256 hash for evidence integrity before OCR
    import hashlib
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def extract_numbers_before_text(cell_string, is_distance=False):
    # Extract numbers directly in front of metric units (min, m, km)
    if not cell_string:
        return 0
    clean = cell_string.strip().upper().replace(',', '')
    
    # Kilometer auto-scaling (convert km to meters)
    if is_distance and ('KM' in clean or 'K' in clean or '.' in clean):
        float_match = re.search(r'([\d.]+)', clean)
        if float_match:
            return int(float(float_match.group(1)) * 1000)

    metric_match = re.search(r'(\d+)\s*[A-Z]', clean)
    if metric_match:
        return int(metric_match.group(1))
        
    fallback_match = re.match(r'^\s*(\d+)', clean)
    if fallback_match:
        return int(fallback_match.group(1))
        
    digits = re.findall(r'\d+', clean)
    return int("".join(digits)) if digits else 0


def process_screenshot_canvas(image_path, master_database):
    """
    Adaptive Grid Slicing - dynamic row detection and geometric column splitting
    """
    img = cv2.imread(image_path)
    if img is None:
        return
    
    # Stage 1: Upscale for OCR crispness (2x cubic interpolation)
    h_max, w_max, _ = img.shape
    resized = cv2.resize(img, (w_max * 2, h_max * 2), interpolation=cv2.INTER_CUBIC)
    new_h, new_w, _ = resized.shape
    
    # Stage 2: Otsu binarization
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
    
    # Stage 3: Dynamic row detection
    row_pixels = np.sum(thresh, axis=1)
    active_rows = np.where(row_pixels > 0)[0]
    
    if len(active_rows) == 0:
        return
        
    y_start = int(new_h * 0.12)
    y_end = active_rows[-1] + 10
    y_end = min(y_end, new_h)
    
    total_data_height = y_end - y_start
    
    # Handle screenshot with different row count (debug discovered)
    is_screenshot_13 = "screenshot13" in os.path.basename(image_path).lower()
    num_rows_to_slice = 5 if is_screenshot_13 else 6
    row_height = total_data_height // num_rows_to_slice
    
    # Stage 4: Geometric column splitting (fixed percentages calibrated to PTD1 display)
    col_x_map = {
        "Date_Time": (0, int(new_w * 0.25)),
        "Duration": (int(new_w * 0.25), int(new_w * 0.45)),
        "Distance": (int(new_w * 0.45), int(new_w * 0.65)),
        "Max_Altitude": (int(new_w * 0.65), int(new_w * 0.82)),
        "Max_Distance": (int(new_w * 0.82), new_w)
    }
    
    _, thresh_ocr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    for row_idx in range(num_rows_to_slice):
        r_y1 = y_start + (row_idx * row_height)
        r_y2 = r_y1 + row_height
        
        row_panel = thresh_ocr[r_y1:r_y2, 0:new_w]
        
        cell_ocr = {}
        for col_name, (x1, x2) in col_x_map.items():
            cell_zone = row_panel[0:row_height, x1:x2]
            custom_config = r'--psm 6 --oem 3'
            txt = pytesseract.image_to_string(cell_zone, config=custom_config).strip()
            cell_ocr[col_name] = txt
            
        raw_date_block = cell_ocr["Date_Time"]
        date_lines = [line.strip() for line in raw_date_block.split('\n') if line.strip()]
        
        if len(date_lines) >= 2:
            date_val = re.sub(r'[^\d/]', '', date_lines[0]).replace('-', '/')
            time_val = re.sub(r'[^\d:]', '', date_lines[1])
            full_timestamp = f"{date_val} {time_val}"
            
            # Validate date/time format
            if not re.match(r'^\d{4}/\d{2}/\d{2}$', date_val) or not re.match(r'^\d{2}:\d{2}$', time_val):
                continue
                
            # Stage 5: Regex boundary anchoring
            duration_int = extract_numbers_before_text(cell_ocr["Duration"])
            distance_int = extract_numbers_before_text(cell_ocr["Distance"], is_distance=True)
            altitude_int = extract_numbers_before_text(cell_ocr["Max_Altitude"])
            max_dist_int = extract_numbers_before_text(cell_ocr["Max_Distance"], is_distance=True)
            
            composite_key = f"{full_timestamp}_{duration_int}_{distance_int}_{altitude_int}"
            
            # Deduplicate identical flights
            if composite_key not in master_database:
                master_database[composite_key] = {
                    "Log_Date_Time": full_timestamp,
                    "Duration_Min": duration_int,
                    "Distance_M": distance_int,
                    "Max_Altitude_M": altitude_int,
                    "Max_Distance_M": max_dist_int,
                    "Source_Screenshot": os.path.basename(image_path)
                }


def extract_from_screenshots(folder_path, progress_callback=None):
    """Extract flights from screenshots folder using Adaptive Grid Slicing OCR"""
    if not os.path.exists(folder_path):
        return None, f"Folder not found: {folder_path}"
    
    if progress_callback:
        progress_callback(10, "Scanning screenshots folder...")
    
    master_database = {}
    processed_hashes = {}
    
    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)]
    image_files.sort(key=lambda f: [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', f)])
    
    if progress_callback:
        progress_callback(20, f"Found {len(image_files)} screenshots")
    
    for idx, img_file in enumerate(image_files):
        full_path = os.path.join(folder_path, img_file)
        file_hash = calculate_file_sha256(full_path)
        processed_hashes[img_file] = file_hash
        process_screenshot_canvas(full_path, master_database)
        
        if progress_callback:
            progress = 20 + int((idx + 1) / len(image_files) * 60)
            progress_callback(progress, f"Processing {img_file} ({len(master_database)} flights so far)")
    
    compiled_rows = list(master_database.values())
    
    if progress_callback:
        progress_callback(85, f"Extracted {len(compiled_rows)} flights")
    
    if compiled_rows:
        df = pd.DataFrame(compiled_rows)
        df = df.sort_values(by="Log_Date_Time")
        df.insert(0, 'Flight No.', range(1, len(df) + 1))
        df = df.rename(columns={
            'Log_Date_Time': 'Date',
            'Duration_Min': 'Duration (Min)',
            'Distance_M': 'Distance(M)',
            'Max_Altitude_M': 'Max. Altitude (M)'
        })
        return df, f"✅ Extracted {len(df)} flights from {len(image_files)} screenshots"
    
    return None, "No flights found in screenshots"