"""CSV exporter with per-row SHA-256 hashing"""

import csv
import os
import json
import hashlib
from datetime import datetime


def calculate_row_hash(flight_no, date_time, duration, distance, altitude, flight_type):
    """Calculate SHA-256 hash for a single flight row"""
    hash_string = f"{flight_no}|{date_time}|{duration}|{distance}|{altitude}|{flight_type}"
    return hashlib.sha256(hash_string.encode('utf-8')).hexdigest()


def export_flights_with_row_hashing(flights_data, output_path, case_number, examiner):
    # Exports CSV with per-row SHA-256 hashes. Returns (csv_path, manifest_path, message)
    
    if not flights_data:
        return None, None, "No flight data to export"
    
    columns = ['Flight_No', 'Date_Time', 'Duration_Min', 'Distance_M', 'Altitude_M', 'Flight_Type']
    
    rows_for_csv = []
    row_hashes = {}
    
    for flight in flights_data:
        flight_no = flight.get('flight_no', '')
        date_time = flight.get('date_time', '')
        duration = flight.get('duration_min', 0)
        distance = flight.get('distance_m', 0)
        altitude = flight.get('altitude_m', 0)
        flight_type = "ABORTED" if (distance == 0 and duration < 2) else "NORMAL"
        
        row_list = [flight_no, date_time, duration, distance, altitude, flight_type]
        rows_for_csv.append(row_list)
        
        row_hash = calculate_row_hash(flight_no, date_time, duration, distance, altitude, flight_type)
        row_hashes[str(flight_no)] = row_hash
    
    # Write CSV with hash column
    csv_path = output_path
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns + ['Row_SHA256_Hash'])
        
        for i, row in enumerate(rows_for_csv):
            flight_no = str(row[0])
            writer.writerow(row + [row_hashes.get(flight_no, '')])
    
    # Create hash manifest file
    manifest_path = output_path.replace('.csv', '.hash.json')
    manifest = {
        "export_info": {
            "timestamp": datetime.now().isoformat(),
            "case_number": case_number,
            "examiner": examiner,
            "hash_algorithm": "SHA-256",
            "csv_file": os.path.basename(csv_path),
            "total_rows": len(rows_for_csv)
        },
        "row_hashes": row_hashes,
        "verification_instructions": "To verify a row, recalculate SHA-256 of 'Flight_No|Date_Time|Duration_Min|Distance_M|Altitude_M|Flight_Type' and compare to stored hash."
    }
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    return csv_path, manifest_path, f"✅ Exported {len(rows_for_csv)} flights with per-row hashes"


def verify_csv_hashes(csv_path):
    # Verifies CSV integrity using stored per-row SHA-256 hashes
    
    if not os.path.exists(csv_path):
        return False, None, f"File not found: {csv_path}"
    
    manifest_path = csv_path.replace('.csv', '.hash.json')
    if not os.path.exists(manifest_path):
        return False, None, f"Hash manifest not found: {manifest_path}"
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        stored_row_hashes = manifest.get('row_hashes', {})
    except Exception as e:
        return False, None, f"Failed to read hash manifest: {str(e)}"
    
    results = {
        "file": csv_path,
        "manifest": manifest_path,
        "verified_at": datetime.now().isoformat(),
        "total_rows": 0,
        "valid_rows": 0,
        "invalid_rows_list": [],
        "valid_rows_list": []
    }
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            if 'Row_SHA256_Hash' not in header:
                return False, None, "CSV file does not contain Row_SHA256_Hash column."
            
            col_indices = {
                'Flight_No': header.index('Flight_No') if 'Flight_No' in header else None,
                'Date_Time': header.index('Date_Time') if 'Date_Time' in header else None,
                'Duration_Min': header.index('Duration_Min') if 'Duration_Min' in header else None,
                'Distance_M': header.index('Distance_M') if 'Distance_M' in header else None,
                'Altitude_M': header.index('Altitude_M') if 'Altitude_M' in header else None,
                'Flight_Type': header.index('Flight_Type') if 'Flight_Type' in header else None,
                'hash_col': header.index('Row_SHA256_Hash')
            }
            
            for row_num, row in enumerate(reader, start=1):
                results['total_rows'] += 1
                
                flight_no = row[col_indices['Flight_No']].strip() if col_indices['Flight_No'] is not None else str(row_num)
                date_time = row[col_indices['Date_Time']] if col_indices['Date_Time'] is not None else ''
                duration = row[col_indices['Duration_Min']] if col_indices['Duration_Min'] is not None else 0
                distance = row[col_indices['Distance_M']] if col_indices['Distance_M'] is not None else 0
                altitude = row[col_indices['Altitude_M']] if col_indices['Altitude_M'] is not None else 0
                flight_type = row[col_indices['Flight_Type']] if col_indices['Flight_Type'] is not None else ''
                stored_hash = row[col_indices['hash_col']] if col_indices['hash_col'] < len(row) else ''
                
                # Get the expected hash from manifest using flight number
                expected_hash = stored_row_hashes.get(flight_no, stored_row_hashes.get(str(flight_no), None))
                
                if not expected_hash:
                    results['invalid_rows_list'].append({
                        'row': row_num,
                        'flight_no': flight_no,
                        'reason': 'No matching hash in manifest'
                    })
                    continue
                
                # Recalculate hash
                calculated_hash = calculate_row_hash(flight_no, date_time, duration, distance, altitude, flight_type)
                
                if calculated_hash == expected_hash:
                    results['valid_rows'] += 1
                    results['valid_rows_list'].append({'row': row_num, 'flight_no': flight_no})
                else:
                    results['invalid_rows_list'].append({
                        'row': row_num,
                        'flight_no': flight_no,
                        'calculated_hash': calculated_hash[:16] + "...",
                        'expected_hash': expected_hash[:16] + "...",
                        'reason': 'Hash mismatch - data may have been altered'
                    })
            
            is_valid = results['valid_rows'] == results['total_rows']
            
            if is_valid:
                message = f"✅ All {results['total_rows']} rows verified successfully."
            elif results['valid_rows'] > 0:
                message = f"⚠️ Partial: {results['valid_rows']} valid, {len(results['invalid_rows_list'])} invalid"
            else:
                message = f"❌ Verification failed: 0 valid rows"
            
            return is_valid, results, message
            
    except Exception as e:
        return False, None, f"Verification error: {str(e)}"