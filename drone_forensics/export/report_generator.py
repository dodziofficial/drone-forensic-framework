"""Forensic report generator"""

from datetime import datetime


def generate_forensic_report(flight_stats, integrity, drone_name, case_number, examiner, output="forensic_report.txt"):
    """Generate a complete forensic report"""
    with open(output, 'w') as f:
        f.write("="*70 + "\n")
        f.write("FORENSIC REPORT\n")
        f.write("="*70 + "\n")
        f.write(f"Drone: {drone_name}\n")
        f.write(f"Case Number: {case_number}\n")
        f.write(f"Examiner: {examiner}\n")
        f.write(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")
        
        f.write("INTEGRITY VERIFICATION:\n")
        f.write("-"*40 + "\n")
        f.write("  Method: SHA-256 Cryptographic Hashing\n")
        f.write("  Full chain of custody requires personnel tracking.\n\n")
        
        f.write("FLIGHT ANALYSIS RESULTS:\n")
        f.write("-"*40 + "\n")
        f.write(f"  Total Flights: {flight_stats['total']}\n")
        f.write(f"  Normal Flights: {flight_stats['normal']}\n")
        f.write(f"  Aborted Takeoffs: {flight_stats['aborted']}\n")
        f.write(f"  Total Distance: {flight_stats['total_distance_km']:.2f} km\n")
        f.write(f"  Total Flight Time: {flight_stats['total_hours']:.1f} hours\n")
        f.write(f"  Maximum Altitude: {flight_stats['max_altitude']} m\n\n")
        
        if flight_stats.get('aborted_list'):
            f.write("ABORTED TAKEOFFS:\n")
            f.write("-"*40 + "\n")
            for a in flight_stats['aborted_list'][:20]:
                f.write(f"  Flight {a['flight_no']}: {a['date_time']} - {a['duration_min']} min, {a['distance_m']} m\n")
            f.write("\n")
        
        if integrity.gps_photos:
            f.write("GPS DATA FROM PHOTOS:\n")
            f.write("-"*40 + "\n")
            for p in integrity.gps_photos:
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