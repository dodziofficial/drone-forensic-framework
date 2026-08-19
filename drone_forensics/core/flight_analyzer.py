"""Flight analyzer - classifies and analyzes flight data"""

import os
import re
import pandas as pd
from datetime import datetime
from drone_forensics.core.integrity import EvidenceIntegrity


class ForensicFramework:
    def __init__(self, case_number, examiner, drone_config=None):
        self.case_number = case_number
        self.examiner = examiner
        self.drone_config = drone_config or {"name": "Potensic Atom 2"}
        self.integrity = EvidenceIntegrity(case_number, examiner)
        self.flight_stats = {}
        self.photos = []
        self.media_path = None
        self.progress_callback = None
        self.drone_key = self.drone_config.get('key', 'unknown')
    
    def set_progress_callback(self, callback):
        self.progress_callback = callback
    
    def report_progress(self, percent, message):
        if self.progress_callback:
            self.progress_callback(percent, message)
    
    def set_media_path(self, path):
        self.media_path = path
        if os.path.exists(path):
            self.integrity.add_evidence(path, "SD Card Media", f"Folder with {len(os.listdir(path))} files")
            self._scan_media()
    
    def _scan_media(self):
        if not self.media_path:
            return
        
        self.report_progress(70, "Scanning media files for GPS data...")
        
        for filename in os.listdir(self.media_path):
            filepath = os.path.join(self.media_path, filename)
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                self.integrity.add_evidence(filepath, "SD Card Media", "Photo from flight")
    
    def load_flights(self, df):
        """Load flights from DataFrame - handles Potensic AND DJI formats"""
        flights = []
        
        # STRIP SPACES FROM COLUMN NAMES (critical for DJI)
        df.columns = df.columns.str.strip()
        
        # Check if this is DJI Mavic Pro data
        is_dji_pro = self.drone_key == 'dji_mavic_pro'
        
        if is_dji_pro:
            # ============================================================
            # DJI MAVIC PRO PARSING (from standalone parser)
            # ============================================================
            print("📡 Using DJI Mavic Pro column mapping")
            
            date_col = 'CUSTOM.date [local]'
            time_col = 'CUSTOM.updateTime [local]'
            dur_col = 'OSD.flyTime'
            dist_col = 'DETAILS.totalDistance [ft]'
            alt_col = 'OSD.height [ft]'
            lat_col = 'OSD.latitude'
            lon_col = 'OSD.longitude'
            bat_col = 'BATTERY.chargeLevel'
            flight_id_col = 'RECOVER.aircraftSerial'
            
            # Check columns
            for col in [lat_col, lon_col, alt_col, dist_col, dur_col, bat_col, date_col]:
                if col in df.columns:
                    print(f"   ✅ Column '{col}' found")
                else:
                    print(f"   ❌ Column '{col}' NOT found")
            
            valid_count = 0
            for idx, row in df.iterrows():
                try:
                    # Get date and time
                    date_val = str(row.get(date_col, ''))
                    time_val = str(row.get(time_col, '')) if time_col else ''
                    
                    if not date_val or date_val == 'nan':
                        continue
                    
                    date_time = f"{date_val} {time_val}".strip() if time_val and time_val != 'nan' else date_val
                    
                    # Parse duration from OSD.flyTime
                    duration_min = 0
                    dur_val = row.get(dur_col)
                    if dur_val is not None and not pd.isna(dur_val):
                        dur_str = str(dur_val).strip()
                        if 'm' in dur_str and 's' in dur_str:
                            match = re.search(r'(\d+)m\s+([\d.]+)s', dur_str)
                            if match:
                                minutes = int(match.group(1))
                                seconds = float(match.group(2))
                                duration_min = minutes + (seconds / 60)
                        else:
                            try:
                                duration_min = float(dur_str)
                            except:
                                duration_min = 0
                    
                    # Get latitude
                    latitude = 0.0
                    lat_val = row.get(lat_col)
                    if lat_val is not None and not pd.isna(lat_val):
                        try:
                            latitude = float(lat_val)
                        except:
                            latitude = 0.0
                    
                    # Get longitude
                    longitude = 0.0
                    lon_val = row.get(lon_col)
                    if lon_val is not None and not pd.isna(lon_val):
                        try:
                            longitude = float(lon_val)
                        except:
                            longitude = 0.0
                    
                    # Get altitude (feet to meters)
                    altitude_m = 0
                    alt_val = row.get(alt_col)
                    if alt_val is not None and not pd.isna(alt_val):
                        try:
                            altitude_m = float(alt_val) * 0.3048
                        except:
                            altitude_m = 0
                    
                    # Get distance (feet to meters)
                    distance_m = 0
                    dist_val = row.get(dist_col)
                    if dist_val is not None and not pd.isna(dist_val):
                        try:
                            distance_m = float(dist_val) * 0.3048
                        except:
                            distance_m = 0
                    
                    # Get battery
                    battery = 0
                    bat_val = row.get(bat_col)
                    if bat_val is not None and not pd.isna(bat_val):
                        try:
                            battery = int(float(bat_val))
                        except:
                            battery = 0
                    
                    # Debug first 5 flights
                    if valid_count < 5:
                        print(f"  Sample flight {valid_count+1}:")
                        print(f"    Date: {date_time}")
                        print(f"    Latitude: {latitude:.6f}, Longitude: {longitude:.6f}")
                        print(f"    Altitude: {altitude_m:.1f}m, Distance: {distance_m:.1f}m")
                        print(f"    Duration: {duration_min:.2f}min, Battery: {battery}%")
                    
                    # Add flight
                    flights.append({
                        'flight_no': idx + 1,
                        'date_time': date_time,
                        'duration_min': duration_min,
                        'distance_m': distance_m,
                        'altitude_m': altitude_m,
                        'latitude': latitude,
                        'longitude': longitude,
                        'battery': battery,
                        'flight_id': f'FLIGHT_{idx+1}'
                    })
                    valid_count += 1
                    
                except Exception as e:
                    print(f"Warning: Could not parse row {idx}: {e}")
                    continue
            
            print(f"✅ Loaded {len(flights)} DJI flights")
            
        else:
            # ============================================================
            # POTENSIC ATOM 2 / OTHER DRONES PARSING (Original Code)
            # ============================================================
            
            # Try to detect column names
            if 'Date' in df.columns and 'Duration (Min)' in df.columns:
                date_col = 'Date'
                dur_col = 'Duration (Min)'
                dist_col = 'Distance(M)'
                alt_col = 'Max. Altitude (M)'
            elif 'Log_Date_Time' in df.columns:
                date_col = 'Log_Date_Time'
                dur_col = 'Duration_Min'
                dist_col = 'Distance_M'
                alt_col = 'Max_Altitude_M'
            else:
                # Auto-detect
                date_col = None
                dur_col = None
                dist_col = None
                alt_col = None
                for col in df.columns:
                    if 'date' in col.lower() or 'time' in col.lower():
                        if date_col is None:
                            date_col = col
                    if 'duration' in col.lower():
                        if dur_col is None:
                            dur_col = col
                    if 'distance' in col.lower():
                        if dist_col is None:
                            dist_col = col
                    if 'altitude' in col.lower():
                        if alt_col is None:
                            alt_col = col
                
                if date_col is None:
                    date_col = df.columns[0] if len(df.columns) > 0 else None
            
            for idx, row in df.iterrows():
                try:
                    flight_no = int(row.get('Flight No.', idx + 1))
                    date_time = str(row[date_col]) if date_col and date_col in row else ""
                    duration = float(row[dur_col]) if dur_col and dur_col in row else 0
                    distance = float(row[dist_col]) if dist_col and dist_col in row else 0
                    altitude = float(row[alt_col]) if alt_col and alt_col in row else 0
                    
                    flights.append({
                        'flight_no': flight_no,
                        'date_time': date_time,
                        'duration_min': duration,
                        'distance_m': distance,
                        'altitude_m': altitude
                    })
                except Exception as e:
                    print(f"Warning: Could not parse row {idx}: {e}")
                    continue
            
            print(f"✅ Loaded {len(flights)} flights")
        
        self.integrity.log_action("Data Loaded", f"{len(flights)} flights from CSV")
        return flights
    
    def analyze_flights(self, flights):
        self.report_progress(75, "Analyzing flight data")
        
        # A flight is normal if it has distance > 0 OR duration >= 2 minutes
        normal = [f for f in flights if not (f.get('distance_m', 0) == 0 and f.get('duration_min', 0) < 2)]
        aborted = [f for f in flights if f.get('distance_m', 0) == 0 and f.get('duration_min', 0) < 2]
        
        # Count flights with GPS data
        gps_flights = len([f for f in flights if f.get('latitude', 0) != 0 or f.get('longitude', 0) != 0])
        
        total_distance_km = sum(f.get('distance_m', 0) for f in flights) / 1000
        total_hours = sum(f.get('duration_min', 0) for f in flights) / 60
        max_altitude = max(f.get('altitude_m', 0) for f in flights) if flights else 0
        
        print(f"📊 Analysis: {len(flights)} flights, {len(normal)} normal, {len(aborted)} aborted")
        print(f"📊 GPS data present in {gps_flights} flights")
        
        self.flight_stats = {
            'total': len(flights),
            'normal': len(normal),
            'aborted': len(aborted),
            'gps_flights': gps_flights,
            'total_distance_km': total_distance_km,
            'total_hours': total_hours,
            'max_altitude': max_altitude,
            'all_flights': flights,
            'aborted_list': aborted
        }
        
        self.integrity.log_action("Analysis Complete", 
            f"Total: {self.flight_stats['total']}, Normal: {self.flight_stats['normal']}, Aborted: {self.flight_stats['aborted']}")
        
        return self.flight_stats
    
    def get_flights_for_export(self):
        return self.flight_stats.get('all_flights', [])
    
    def generate_report(self, output="forensic_report.txt"):
        with open(output, 'w') as f:
            f.write("="*70 + "\n")
            f.write("FORENSIC REPORT\n")
            f.write("="*70 + "\n")
            f.write(f"Drone: {self.drone_config.get('name', 'Unknown')}\n")
            f.write(f"Case Number: {self.case_number}\n")
            f.write(f"Examiner: {self.examiner}\n")
            f.write(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*70 + "\n\n")
            
            f.write("INTEGRITY VERIFICATION:\n")
            f.write("-"*40 + "\n")
            f.write("  Method: SHA-256 Cryptographic Hashing\n")
            f.write("  NOTE: This is INTEGRITY VERIFICATION only.\n")
            f.write("  Full chain of custody requires personnel tracking.\n\n")
            
            f.write("FLIGHT ANALYSIS RESULTS:\n")
            f.write("-"*40 + "\n")
            f.write(f"  Total Flights: {self.flight_stats['total']}\n")
            f.write(f"  Normal Flights: {self.flight_stats['normal']}\n")
            f.write(f"  Aborted Takeoffs: {self.flight_stats['aborted']}\n")
            f.write(f"  Flights with GPS: {self.flight_stats.get('gps_flights', 0)}\n")
            f.write(f"  Total Distance: {self.flight_stats['total_distance_km']:.2f} km\n")
            f.write(f"  Total Flight Time: {self.flight_stats['total_hours']:.1f} hours\n")
            f.write(f"  Maximum Altitude: {self.flight_stats['max_altitude']:.1f} m\n\n")
            
            if self.flight_stats['aborted_list']:
                f.write("ABORTED TAKEOFFS:\n")
                f.write("-"*40 + "\n")
                for a in self.flight_stats['aborted_list'][:20]:
                    f.write(f"  Flight {a['flight_no']}: {a['date_time']} - {a['duration_min']:.1f} min, {a['distance_m']:.0f} m\n")
                f.write("\n")
            
            if self.integrity.gps_photos:
                f.write("GPS DATA FROM PHOTOS:\n")
                f.write("-"*40 + "\n")
                for p in self.integrity.gps_photos:
                    g = p['gps']
                    f.write(f"\n  File: {p['file']}")
                    f.write(f"\n    GPS Coordinates: {g.get('latitude', 'N/A')}, {g.get('longitude', 'N/A')}")
                    if g.get('altitude'):
                        f.write(f"\n    Altitude: {g['altitude']} m")
                    if g.get('timestamp'):
                        f.write(f"\n    Photo Taken: {g['timestamp']}")
                    if g.get('make') and g.get('model'):
                        f.write(f"\n    Camera: {g['make']} {g['model']}")
                    f.write("\n")
        
        print(f"✅ Report saved: {output}")
        return output
    
    def save_reports(self):
        self.report_progress(100, "Saving reports")
        self.generate_report()
        self.integrity.save_log()
        print("✅ Reports saved: forensic_report.txt, integrity_log.json")