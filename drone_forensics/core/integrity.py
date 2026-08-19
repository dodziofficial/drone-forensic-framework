"""Evidence integrity - SHA-256 hashing for forensic evidence"""

import os
import hashlib
import json
from datetime import datetime
from drone_forensics.core.gps_extractor import extract_gps_from_photo, extract_gps_with_pil


class EvidenceIntegrity:
    def __init__(self, case_number, examiner):
        self.case_number = case_number
        self.examiner = examiner
        self.acquisition_time = datetime.now()
        self.evidence = []
        self.actions = []
        self.gps_photos = []
    
    def add_evidence(self, file_path, source, description=""):
        if os.path.exists(file_path) and not os.path.isdir(file_path):
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for block in iter(lambda: f.read(65536), b''):
                    sha256.update(block)
            hash_val = sha256.hexdigest()
            
            gps_info = None
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                gps_info = extract_gps_from_photo(file_path)
                if not gps_info:
                    gps_info = extract_gps_with_pil(file_path)
                if gps_info and gps_info.get('has_gps'):
                    self.gps_photos.append({
                        'file': os.path.basename(file_path),
                        'gps': gps_info
                    })
            
            self.evidence.append({
                'file': os.path.basename(file_path),
                'source': source,
                'sha256': hash_val[:32] + "...",
                'time': datetime.now().isoformat(),
                'description': description,
                'size': os.path.getsize(file_path),
                'gps_info': gps_info
            })
    
    def log_action(self, action, description):
        self.actions.append({
            'time': datetime.now().isoformat(),
            'action': action,
            'description': description
        })
    
    def get_report(self):
        report = []
        report.append("="*70)
        report.append("EVIDENCE INTEGRITY REPORT (SHA-256)")
        report.append("="*70)
        report.append(f"Case Number: {self.case_number}")
        report.append(f"Examiner: {self.examiner}")
        report.append(f"Acquisition Date: {self.acquisition_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("NOTE: This is INTEGRITY VERIFICATION only, not full chain of custody.")
        report.append("")
        
        report.append("EVIDENCE LOG:")
        report.append("-"*50)
        
        for i, e in enumerate(self.evidence, 1):
            report.append(f"\nEvidence #{i}: {e['file']}")
            report.append(f"  Source: {e['source']}")
            report.append(f"  Size: {e['size']} bytes")
            report.append(f"  SHA-256: {e['sha256']}")
            report.append(f"  Time Added: {e['time'][:19]}")
            report.append(f"  Description: {e['description']}")
            
            if e.get('gps_info') and e['gps_info'].get('has_gps'):
                g = e['gps_info']
                report.append(f"  GPS Coordinates: {g.get('latitude', 'N/A')}, {g.get('longitude', 'N/A')}")
                if g.get('altitude'):
                    report.append(f"  GPS Altitude: {g['altitude']} m")
                if g.get('timestamp'):
                    report.append(f"  Photo Taken: {g['timestamp']}")
                if g.get('make') and g.get('model'):
                    report.append(f"  Camera: {g['make']} {g['model']}")
        
        if self.gps_photos:
            report.append("\n" + "-"*50)
            report.append("GPS-ENABLED PHOTOS SUMMARY:")
            report.append("-"*50)
            for p in self.gps_photos:
                g = p['gps']
                report.append(f"\n  File: {p['file']}")
                report.append(f"    Coordinates: {g.get('latitude', 'N/A')}, {g.get('longitude', 'N/A')}")
                if g.get('altitude'):
                    report.append(f"    Altitude: {g['altitude']} m")
                if g.get('timestamp'):
                    report.append(f"    Taken: {g['timestamp']}")
        
        if self.actions:
            report.append("\n" + "-"*50)
            report.append("ACTION LOG:")
            report.append("-"*50)
            for a in self.actions:
                report.append(f"  [{a['time'][:19]}] {a['action']}: {a['description']}")
        
        return "\n".join(report)
    
    def save_log(self, path="integrity_log.json"):
        json_evidence = []
        for e in self.evidence:
            json_item = {
                'file': e['file'],
                'source': e['source'],
                'sha256': e['sha256'],
                'time': e['time'],
                'description': e['description'],
                'size': e['size']
            }
            if e.get('gps_info') and e['gps_info'].get('has_gps'):
                json_item['gps'] = {
                    'latitude': e['gps_info'].get('latitude'),
                    'longitude': e['gps_info'].get('longitude'),
                    'altitude': e['gps_info'].get('altitude'),
                    'timestamp': e['gps_info'].get('timestamp')
                }
            json_evidence.append(json_item)
        
        data = {
            "case_number": self.case_number,
            "examiner": self.examiner,
            "acquisition_time": self.acquisition_time.isoformat(),
            "integrity_method": "SHA-256",
            "note": "INTEGRITY VERIFICATION only - not chain of custody",
            "evidence": json_evidence,
            "actions": self.actions,
            "gps_photos_count": len(self.gps_photos)
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        return path