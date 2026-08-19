"""GPS extractor - EXIF GPS data from photos using exiftool or PIL fallback"""

import os
import re
import subprocess
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


def dms_to_decimal(degrees, minutes, seconds, reference):
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if reference in ['S', 'W']:
        decimal = -decimal
    return decimal


def parse_dms_string(dms_str):
    pattern = r'(\d+)\s+deg\s+(\d+)\'\s+([\d.]+)"\s+([NSEW])'
    match = re.search(pattern, dms_str)
    if match:
        deg = float(match.group(1))
        minutes = float(match.group(2))
        sec = float(match.group(3))
        ref = match.group(4)
        return dms_to_decimal(deg, minutes, sec, ref)
    return None


def extract_gps_from_photo(filepath):
    """Extract GPS EXIF data from photo using exiftool"""
    exiftool_paths = [
        "exiftool.exe",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "exiftool.exe"),
        "C:\\exiftool\\exiftool.exe",
    ]
    
    exiftool_path = None
    for path in exiftool_paths:
        if os.path.exists(path):
            exiftool_path = path
            break
    
    if not exiftool_path:
        try:
            result = subprocess.run(['where', 'exiftool'], capture_output=True, text=True)
            if result.stdout.strip():
                exiftool_path = result.stdout.strip().split('\n')[0]
        except:
            pass
    
    if not exiftool_path:
        return None
    
    try:
        result = subprocess.run(
            [exiftool_path, '-GPSLatitude', '-GPSLongitude', '-GPSAltitude', 
             '-GPSLatitudeRef', '-GPSLongitudeRef', '-Make', '-Model', 
             '-DateTimeOriginal', filepath],
            capture_output=True, text=True, timeout=10
        )
        
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            gps_data = {'has_gps': False}
            
            for line in lines:
                if ':' not in line:
                    continue
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if key == 'GPS Latitude':
                    lat_decimal = parse_dms_string(value)
                    if lat_decimal is not None:
                        gps_data['latitude'] = lat_decimal
                        gps_data['has_gps'] = True
                
                elif key == 'GPS Longitude':
                    lon_decimal = parse_dms_string(value)
                    if lon_decimal is not None:
                        gps_data['longitude'] = lon_decimal
                        gps_data['has_gps'] = True
                
                elif key == 'GPS Altitude':
                    alt_match = re.search(r'([\d.]+)', value)
                    if alt_match:
                        gps_data['altitude'] = float(alt_match.group(1))
                
                elif key == 'Make':
                    gps_data['make'] = value
                
                elif key == 'Camera Model Name':
                    gps_data['model'] = value
                
                elif key == 'Date/Time Original':
                    gps_data['timestamp'] = value
            
            return gps_data
    except:
        pass
    
    return None


def extract_gps_with_pil(filepath):
    """Alternative GPS extraction using PIL (no exiftool needed)"""
    try:
        image = Image.open(filepath)
        exif_data = image._getexif()
        
        if not exif_data:
            return None
        
        gps_info = {}
        
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'GPSInfo':
                for gps_tag in value:
                    gps_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                    gps_info[gps_tag_name] = value[gps_tag]
        
        if not gps_info:
            return None
        
        def convert_to_degrees(value):
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
        
        gps_data = {'has_gps': False}
        
        if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
            lat = convert_to_degrees(gps_info['GPSLatitude'])
            lon = convert_to_degrees(gps_info['GPSLongitude'])
            
            if gps_info.get('GPSLatitudeRef') == 'S':
                lat = -lat
            if gps_info.get('GPSLongitudeRef') == 'W':
                lon = -lon
            
            gps_data['latitude'] = lat
            gps_data['longitude'] = lon
            gps_data['has_gps'] = True
            
            if 'GPSAltitude' in gps_info:
                gps_data['altitude'] = float(gps_info['GPSAltitude'])
            
            if 'DateTime' in exif_data:
                gps_data['timestamp'] = exif_data['DateTime']
            
            return gps_data
        
        return None
    except Exception as e:
        return None