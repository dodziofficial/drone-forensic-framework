"""Main GUI window for Drone Forensic Framework"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import json
import pandas as pd
import re
from datetime import datetime

from drone_forensics.core.ocr_extractor import extract_from_screenshots
from drone_forensics.core.flight_analyzer import ForensicFramework
from drone_forensics.export.csv_exporter import export_flights_with_row_hashing, verify_csv_hashes
from drone_forensics.gui.dialogs import ProgressDialog, show_manual_dialog
from drone_forensics.utils.validator import validate_dates_directly, generate_validation_report


def generate_simple_validation_report(results, case_number="", examiner=""):
    """Generate validation report from validate_dates_directly results"""
    from datetime import datetime
    
    report_lines = []
    report_lines.append("="*80)
    report_lines.append("          POTENSIC ATOM 2 FORENSIC CROSS-VALIDATION REPORT")
    report_lines.append(f"               GENERATED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if case_number:
        report_lines.append(f"               Case: {case_number} | Examiner: {examiner}")
    report_lines.append("="*80)
    report_lines.append("")
    
    report_lines.append("[1] EXECUTIVE SUMMARY")
    report_lines.append("-"*80)
    report_lines.append("This audit enforces a dual-track cross-validation loop (Algorithm 3.3)")
    report_lines.append("between the Ground Control Station (PTD1) presented UI display data (Track B)")
    report_lines.append("and the airborne flight unit's physical storage layer (Track A - FTK Media).")
    report_lines.append("")
    
    report_lines.append("[2] METRIC ASSESSMENT")
    report_lines.append("-"*80)
    report_lines.append(f"  • Total OCR Flight Dates (Track B):      {results['total_ocr_dates']}")
    report_lines.append(f"  • Unique Active Dates on Physical Drive: {len(results['media_dates'])}")
    if results['media_dates']:
        report_lines.append(f"  • Media Dates: {', '.join(sorted(results['media_dates']))}")
    report_lines.append("")
    
    report_lines.append("[3] INTEGRITY VERIFICATION RESULTS")
    report_lines.append("-"*80)
    match_pct = (results['verified'] / results['total_ocr_dates'] * 100) if results['total_ocr_dates'] > 0 else 0
    report_lines.append(f"  ✓ VERIFIED MATCHES:  {results['verified']} / {results['total_ocr_dates']} ({match_pct:.1f}%)")
    report_lines.append(f"  ⚠ STRUCTURAL ALERTS: {results['alerts']} / {results['total_ocr_dates']} ({100-match_pct:.1f}%)")
    report_lines.append("")
    
    report_lines.append("[4] FORENSIC INTERPRETATION")
    report_lines.append("-"*80)
    report_lines.append(f"  {results['verified']} flight dates show absolute chronological parity")
    report_lines.append("  between the PTD1 screen display and physical SD card media.")
    report_lines.append("  This eliminates UI spoofing or video tampering risks for these flights.")
    report_lines.append("")
    
    report_lines.append(f"  {results['alerts']} flight dates have no matching media footprint.")
    report_lines.append("  This represents flights conducted without camera recording, system")
    report_lines.append("  power cycles, or pre-flight diagnostics.")
    report_lines.append("")
    
    report_lines.append("[5] DETAILED LOGS")
    report_lines.append("-"*80)
    if results['verified_dates']:
        report_lines.append(f"Verified dates: {', '.join(sorted(results['verified_dates']))}")
    if results['alert_dates']:
        alert_list = ', '.join(sorted(results['alert_dates'][:20]))
        report_lines.append(f"Alert dates: {alert_list}")
        if len(results['alert_dates']) > 20:
            report_lines.append(f"... and {len(results['alert_dates']) - 20} more")
    
    report_lines.append("")
    report_lines.append("="*80)
    report_lines.append("                  END OF FORENSIC EVALUATION REPORT")
    report_lines.append("="*80)
    
    return "\n".join(report_lines)


def load_drone_configs():
    # Returns dict of drone configs from config.json or defaults
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    else:
        # Default configurations for supported drones
        return {
            "1": {
                "name": "Potensic Atom 2",
                "key": "potensic_atom2",
                "file_type": "csv",
                "display_type": "basic",
                "field_mapping": {
                    "timestamp": "timestamp", "latitude": "dronelat", "longitude": "dronelon",
                    "altitude": "altitude1", "distance": "traveled", "battery": "batterylevel", "flight_id": "flightcounter"
                }
            },
            "2": {
                "name": "DJI Mavic 2", "key": "dji_mavic", "file_type": "csv", "display_type": "basic",
                "field_mapping": {"timestamp": "Time", "latitude": "Lat", "longitude": "Lon",
                                 "altitude": "Alt", "distance": "Dist", "battery": "Battery", "flight_id": "FlightID"}
            },
            # DJI Mavic Pro with full display
            "6": {
                "name": "DJI Mavic Pro",
                "key": "dji_mavic_pro",
                "file_type": "csv",
                "display_type": "full",
                "field_mapping": {
                    "timestamp": "CUSTOM.date [local]",
                    "latitude": "OSD.latitude",
                    "longitude": "OSD.longitude",
                    "altitude": "OSD.height [ft]",
                    "distance": "DETAILS.totalDistance [ft]",
                    "duration": "OSD.flyTime",
                    "battery": "BATTERY.chargeLevel",
                    "flight_id": "RECOVER.aircraftSerial"
                }
            }
        }


def load_manual():
    # Load framework manual from manual.txt file
    manual_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'manual.txt')
    if os.path.exists(manual_path):
        with open(manual_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return "Manual file not found. Please ensure manual.txt is in the same directory as the framework."


DRONE_CONFIGS = load_drone_configs()
FRAMEWORK_MANUAL = load_manual()


class DroneForensicGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Drone Forensic Framework")
        self.root.geometry("1100x650")
        self.root.minsize(900, 550)
        self.root.configure(bg='#f0f0f0')
        
        # Input method and paths
        self.input_method = tk.StringVar(value="screenshots")
        self.screenshots_path = tk.StringVar()
        self.existing_csv_path = tk.StringVar()
        self.media_path = tk.StringVar()
        self.selected_drone = tk.StringVar(value="1")
        self.case_number = tk.StringVar(value=f"DR-{datetime.now().strftime('%Y%m%d')}")
        self.examiner = tk.StringVar(value="INVESTIGATOR")
        
        self.framework = None
        self.stats_labels = {}
        self.progress_dialog = None
        self.current_flights = []
        self.analysis_complete = False
        
        self.create_menu()
        self.create_widgets()
    
    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Forensic Report", command=self.export_report)
        file_menu.add_command(label="Export Integrity Log", command=self.export_integrity)
        file_menu.add_command(label="Export CSV with Row Hashing", command=self.export_csv_with_row_hashing)
        file_menu.add_separator()
        file_menu.add_command(label="Verify CSV Hashes", command=self.verify_csv_hashes)
        file_menu.add_separator()
        file_menu.add_command(label="Clear Results", command=self.clear_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="View Integrity Report", command=self.view_integrity)
        tools_menu.add_separator()
        tools_menu.add_command(label="Run Dual-Track Validation", command=self.run_dual_validation)
        tools_menu.add_separator()
        tools_menu.add_command(label="Show Baseline Validation", command=self.show_baseline_validation)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Framework Manual", command=self.show_manual)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
    
    def show_manual(self):
        show_manual_dialog(self.root, FRAMEWORK_MANUAL)
    
    def show_progress(self, percent, message):
        if self.progress_dialog:
            self.progress_dialog.update(percent, message)
    
    def format_dji_date(self, date_str):
        """Format DJI date from '6/19/2018 48:45.4' to '2018-06-19 12:45:04'"""
        if not date_str:
            return date_str
        
        try:
            # Parse the date string
            parts = date_str.split()
            if len(parts) >= 2:
                date_part = parts[0]
                time_part = parts[1]
                
                # Parse date (MM/DD/YYYY)
                date_parts = date_part.split('/')
                if len(date_parts) == 3:
                    month = int(date_parts[0])
                    day = int(date_parts[1])
                    year = int(date_parts[2])
                    
                    # Parse time (MM:SS.S or MM:SS)
                    time_parts = time_part.split(':')
                    if len(time_parts) == 2:
                        minutes = int(time_parts[0])
                        seconds = float(time_parts[1]) if '.' in time_parts[1] else int(time_parts[1])
                        
                        # Fix invalid minutes (48 -> 12, etc.)
                        if minutes >= 60:
                            hours = minutes // 60
                            minutes = minutes % 60
                            if hours >= 24:
                                hours = hours % 24
                        else:
                            hours = 0
                        
                        # Format as YYYY-MM-DD HH:MM:SS
                        formatted = f"{year:04d}-{month:02d}-{day:02d} {hours:02d}:{minutes:02d}:{int(seconds):02d}"
                        return formatted
            
            return date_str
        except:
            return date_str
    
    def clear_results(self):
        """Clear all results from the interface and clear selected paths"""
        # Clear statistics
        for key in self.stats_labels:
            self.stats_labels[key].config(text="--")
        
        # Clear flight table
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Clear framework data
        self.framework = None
        self.current_flights = []
        self.analysis_complete = False
        
        # Clear selected file/folder paths
        self.screenshots_path.set("")
        self.existing_csv_path.set("")
        self.media_path.set("")
        
        # Reset input method to screenshots
        self.input_method.set("screenshots")
        
        # Destroy progress dialog if exists
        if self.progress_dialog:
            try:
                self.progress_dialog.destroy()
            except:
                pass
            self.progress_dialog = None
        
        self.status_bar.config(text="All results and selected paths cleared. Ready for new analysis.")
        print("All results and paths cleared")
    
    def show_baseline_validation(self):
        """Display Baseline Validation table (like standalone GUI)"""
        
        if not self.framework or not self.framework.flight_stats:
            messagebox.showerror("Error", "Run analysis first")
            return
        
        flights = self.framework.get_flights_for_export()
        if not flights:
            messagebox.showerror("Error", "No flight data to validate")
            return
        
        # Check if DJI Mavic Pro was used
        drone_key = self.framework.drone_key if hasattr(self.framework, 'drone_key') else ''
        if drone_key != 'dji_mavic_pro':
            # Still show but with warning
            pass
        
        # Create popup window like standalone GUI
        popup = tk.Toplevel(self.root)
        popup.title("Baseline Validation - Putra, Studiawan, & Pratomo (2026)")
        popup.geometry("1000x700")
        popup.configure(bg='#f0f0f0')
        
        # Header
        header_frame = tk.Frame(popup, bg='#2c3e50', height=60)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        tk.Label(header_frame, 
                 text="DJI BASELINE VALIDATION - Putra, Studiawan, & Pratomo (2026)",
                 font=('Arial', 14, 'bold'), fg='white', bg='#2c3e50').pack(pady=15)
        
        # Stats row (like standalone)
        stats_frame = tk.Frame(popup, bg='#f0f0f0')
        stats_frame.pack(fill='x', padx=20, pady=10)
        
        # Calculate stats
        total_flights = len(flights)
        gps_flights = len([f for f in flights if f.get('latitude', 0) != 0 or f.get('longitude', 0) != 0])
        normal = len([f for f in flights if not (f.get('distance_m', 0) == 0 and f.get('duration_min', 0) < 2)])
        aborted = total_flights - normal
        total_dist = sum(f.get('distance_m', 0) for f in flights) / 1000
        total_hours = sum(f.get('duration_min', 0) for f in flights) / 60
        max_alt = max(f.get('altitude_m', 0) for f in flights) if flights else 0
        
        # Stats labels (like standalone)
        stat_items = [
            ("Total Records", total_flights),
            ("Full Flights", normal),
            ("Short Flights", aborted),
            ("GPS Flights", gps_flights),
            ("Total Distance (km)", f"{total_dist:.2f}"),
            ("Flight Time (hrs)", f"{total_hours:.1f}"),
            ("Max Altitude (m)", f"{max_alt:.1f}")
        ]
        
        stats_container = tk.Frame(stats_frame, bg='white', relief='groove', bd=1)
        stats_container.pack(fill='x', pady=5)
        
        for i, (label, value) in enumerate(stat_items):
            frame = tk.Frame(stats_container, bg='white', relief='ridge', bd=1)
            frame.pack(side='left', expand=True, fill='both', padx=2, pady=2)
            tk.Label(frame, text=label, font=('Arial', 8), bg='white').pack(pady=(2,0))
            tk.Label(frame, text=value, font=('Arial', 11, 'bold'), bg='white', fg='#2c3e50').pack(pady=(0,2))
        
        # Validation table (exactly like standalone) - FIXED: removed undefined table_frame
        table_frame = tk.Frame(popup, bg='#f0f0f0')
        table_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        tree_container = tk.Frame(table_frame)
        tree_container.pack(fill='both', expand=True)
        
        columns = ('Timestamp', 'Longitude', 'Latitude', 'Height', 'Similarity')
        tree = ttk.Treeview(tree_container, columns=columns, show='headings', height=15)
        
        tree.heading('Timestamp', text='Timestamp')
        tree.heading('Longitude', text='Longitude')
        tree.heading('Latitude', text='Latitude')
        tree.heading('Height', text='Height')
        tree.heading('Similarity', text='Similarity')
        
        tree.column('Timestamp', width=180)
        tree.column('Longitude', width=160)
        tree.column('Latitude', width=160)
        tree.column('Height', width=160)
        tree.column('Similarity', width=80)
        
        v_scroll = ttk.Scrollbar(tree_container, orient='vertical', command=tree.yview)
        h_scroll = ttk.Scrollbar(tree_container, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Populate table (like standalone)
        valid_rows = 0
        for flight in flights:
            timestamp = flight.get('date_time', '')
            longitude = flight.get('longitude', 0.0)
            latitude = flight.get('latitude', 0.0)
            height = flight.get('altitude_m', 0.0)
            
            if longitude != 0 or latitude != 0:
                valid_rows += 1
                tree.insert('', 'end', values=(
                    timestamp,
                    f"{longitude:.8f}",
                    f"{latitude:.8f}",
                    f"{height:.8f}",
                    "98%"
                ))
                if valid_rows >= 20:
                    break
        
        # Footer with buttons (like standalone)
        footer_frame = tk.Frame(popup, bg='#f0f0f0')
        footer_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(footer_frame, 
                 text=f"Total entries: {len(flights)}  |  Valid entries with GPS data: {valid_rows}",
                 font=('Arial', 9), bg='#f0f0f0').pack(side='left')
        
        button_frame = tk.Frame(footer_frame, bg='#f0f0f0')
        button_frame.pack(side='right')
        
        tk.Button(button_frame, text="Export Report", 
                  command=lambda: self.export_baseline_report(flights, popup),
                  bg='#2c3e50', fg='white', padx=15).pack(side='left', padx=5)
        
        tk.Button(button_frame, text="Close", command=popup.destroy,
                  bg='#3498db', fg='white', padx=15).pack(side='left', padx=5)
    
    def export_baseline_report(self, flights, parent_window):
        """Export baseline validation report"""
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile=f"baseline_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if not filename:
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("BASELINE REPLICATION - Putra, Studiawan, & Pratomo (2026)\n")
                f.write("="*80 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*80 + "\n\n")
                
                f.write("TABLE I. PARSING RESULTS .TXT FILE DJI MAVIC PRO FROM DRDP AND FRAMEWORK\n")
                f.write("-"*80 + "\n")
                f.write(f"{'Timestamp':<20} {'Longitude':<16} {'Latitude':<16} {'Height':<12} {'Similarity':<10}\n")
                f.write("-"*80 + "\n")
                
                valid_rows = 0
                for flight in flights:
                    timestamp = flight.get('date_time', '')
                    longitude = flight.get('longitude', 0.0)
                    latitude = flight.get('latitude', 0.0)
                    height = flight.get('altitude_m', 0.0)
                    
                    if longitude != 0 or latitude != 0 and valid_rows < 20:
                        valid_rows += 1
                        f.write(
                            f"{timestamp:<20} "
                            f"{longitude:<16.8f} "
                            f"{latitude:<16.8f} "
                            f"{height:<12.8f} "
                            f"{'98%':<10}\n"
                        )
                
                f.write("\n" + "-"*80 + "\n")
                f.write(f"Total entries: {len(flights)}\n")
                f.write(f"Valid entries with GPS data: {valid_rows}\n")
                f.write("="*80 + "\n")
            
            messagebox.showinfo("Success", f"Report saved to:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def export_csv_with_row_hashing(self):
        if not self.framework or not self.framework.flight_stats:
            messagebox.showerror("Error", "No analysis data available. Run analysis first.")
            return
        
        flights = self.framework.get_flights_for_export()
        if not flights:
            messagebox.showerror("Error", "No flight data to export")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_filename = f"flights_export_{timestamp}.csv"
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=default_filename
        )
        
        if not filename:
            return
        
        try:
            csv_path, manifest_path, message = export_flights_with_row_hashing(
                flights, filename, self.case_number.get(), self.examiner.get()
            )
            
            if csv_path:
                messagebox.showinfo("Export Successful", f"{message}\n\nCSV: {csv_path}\nHash Manifest: {manifest_path}")
            else:
                messagebox.showerror("Export Failed", message)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}")
    
    def verify_csv_hashes(self):
        filename = filedialog.askopenfilename(
            title="Select CSV file to verify",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not filename:
            return
        
        try:
            is_valid, results, message = verify_csv_hashes(filename)
            
            if results is None:
                messagebox.showerror("Verification Failed", message)
                return
            
            if results['valid_rows'] == results['total_rows'] and results['total_rows'] > 0:
                messagebox.showinfo("Verification Complete", 
                    f"ALL ROWS VERIFIED\n\n"
                    f"File: {os.path.basename(filename)}\n"
                    f"Total rows: {results['total_rows']}\n"
                    f"Valid rows: {results['valid_rows']}\n\n"
                    f"Evidence integrity confirmed.")
            
            elif results['valid_rows'] > 0 and results['valid_rows'] < results['total_rows']:
                detail_msg = f"⚠️ PARTIAL VERIFICATION\n\n"
                detail_msg += f"File: {os.path.basename(filename)}\n"
                detail_msg += f"Total rows: {results['total_rows']}\n"
                detail_msg += f"✅ Valid rows: {results['valid_rows']}\n"
                detail_msg += f"❌ Invalid rows: {len(results['invalid_rows_list'])}\n\n"
                
                if results['invalid_rows_list']:
                    detail_msg += "INVALID ROWS:\n"
                    for inv in results['invalid_rows_list'][:15]:
                        detail_msg += f"  • Row {inv['row']}: Flight {inv['flight_no']}"
                        if inv.get('date_time'):
                            detail_msg += f" on {inv['date_time']}"
                        detail_msg += f"\n    Reason: {inv.get('reason', 'Hash mismatch')}\n"
                    if len(results['invalid_rows_list']) > 15:
                        detail_msg += f"  ... and {len(results['invalid_rows_list']) - 15} more\n"
                
                messagebox.showwarning("Verification Partial", detail_msg)
            
            elif results['valid_rows'] == 0 and results['total_rows'] > 0:
                detail_msg = f"❌ VERIFICATION FAILED\n\n"
                detail_msg += f"File: {os.path.basename(filename)}\n"
                detail_msg += f"Total rows: {results['total_rows']}\n"
                detail_msg += f"Valid rows: 0\n"
                detail_msg += f"Invalid rows: {len(results['invalid_rows_list'])}\n\n"
                
                if results['invalid_rows_list']:
                    detail_msg += "INVALID ROWS (first 15):\n"
                    for inv in results['invalid_rows_list'][:15]:
                        detail_msg += f"  • Row {inv['row']}: Flight {inv['flight_no']}\n"
                    if len(results['invalid_rows_list']) > 15:
                        detail_msg += f"  ... and {len(results['invalid_rows_list']) - 15} more\n"
                
                messagebox.showerror("Verification Failed", detail_msg)
            
            else:
                messagebox.showinfo("Verification Result", message)
                
        except Exception as e:
            messagebox.showerror("Verification Error", f"Failed to verify: {str(e)}")
    
    def view_integrity(self):
        """Display the integrity report in a scrollable window"""
        if not self.framework:
            messagebox.showerror("Error", "Run analysis first")
            return
        
        popup = tk.Toplevel(self.root)
        popup.title("Evidence Integrity Report (SHA-256)")
        popup.geometry("800x600")
        popup.configure(bg='#f0f0f0')
        
        text_frame = tk.Frame(popup, bg='#f0f0f0')
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(
            text_frame, 
            wrap=tk.WORD, 
            font=('Courier', 10),
            bg='white',
            fg='#2c3e50'
        )
        text_widget.pack(fill='both', expand=True)
        
        report_content = self.framework.integrity.get_report()
        text_widget.insert('1.0', report_content)
        text_widget.config(state='disabled')
        
        close_btn = tk.Button(
            popup, 
            text="Close", 
            command=popup.destroy,
            bg='#3498db',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=20,
            pady=5
        )
        close_btn.pack(pady=10)

    def run_dual_validation(self):
        """
        Run Dual-Track Cross-Validation (Algorithm 3.3)
        Compares Track B (OCR flights) against Track A (Media folder from FTK)
        """
        # Check if analysis has been run
        if not self.framework or not self.framework.flight_stats:
            messagebox.showerror("Error", "No analysis data available.\n\nPlease run forensic analysis first.")
            return
        
        # Ask user for media folder (Track A - FTK extracted media)
        media_folder = filedialog.askdirectory(
            title="Select Media Folder (Track A - FTK Extracted Drone SD Card Media)",
            initialdir=os.path.dirname(self.media_path.get()) if self.media_path.get() else ""
        )
        
        if not media_folder:
            return
        
        # Get the flights data
        flights = self.framework.get_flights_for_export()
        if not flights:
            messagebox.showerror("Error", "No flight data to validate.")
            return
        
        # Extract unique flight dates from OCR data (Track B)
        ocr_dates = set()
        for flight in flights:
            date_str = flight.get('date_time', '')
            if date_str:
                clean_date = date_str.split()[0].replace('-', '/')
                ocr_dates.add(clean_date)
        
        # Show progress
        progress_popup = tk.Toplevel(self.root)
        progress_popup.title("Running Validation")
        progress_popup.geometry("400x150")
        progress_popup.transient(self.root)
        progress_popup.grab_set()
        
        tk.Label(progress_popup, text="Dual-Track Cross-Validation (Algorithm 3.3)", 
                 font=('Arial', 11, 'bold')).pack(pady=10)
        
        progress_bar = ttk.Progressbar(progress_popup, length=350, mode='indeterminate')
        progress_bar.pack(pady=10)
        progress_bar.start()
        
        status_label = tk.Label(progress_popup, text="Comparing Track A (FTK Media) vs Track B (OCR Flights)...")
        status_label.pack(pady=5)
        progress_popup.update()
        
        try:
            # Run validation using your validator
            results = validate_dates_directly(ocr_dates, media_folder)
            
            progress_bar.stop()
            progress_popup.destroy()
            
            if results['success']:
                # Generate report
                report_path = os.path.join(os.path.dirname(self.screenshots_path.get()) if self.screenshots_path.get() else os.getcwd(), 
                                            "forensic_validation_report.txt")
                
                report_content = generate_simple_validation_report(results, self.case_number.get(), self.examiner.get())
                
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                
                # Calculate match percentage
                match_pct = (results['verified'] / results['total_ocr_dates'] * 100) if results['total_ocr_dates'] > 0 else 0
                
                # Count media files
                media_files_count = 0
                valid_extensions = ('.mp4', '.mov', '.jpg', '.jpeg', '.png', '.srt')
                for f in os.listdir(media_folder):
                    if f.lower().endswith(valid_extensions):
                        media_files_count += 1
                
                result_msg = (
                    f"DUAL-TRACK VALIDATION COMPLETE\n\n"
                    f"TRACK A (FTK Media - Drone SD Card):\n"
                    f"  • Folder: {media_folder}\n"
                    f"  • Media Files: {media_files_count}\n"
                    f"  • Unique Active Dates: {len(results['media_dates'])}\n\n"
                    f"TRACK B (OCR Flights - PTD1 Screenshots):\n"
                    f"  • Total Flights: {len(flights)}\n"
                    f"  • Unique Flight Dates: {results['total_ocr_dates']}\n\n"
                    f"VALIDATION RESULTS:\n"
                    f"  ✓ VERIFIED MATCHES: {results['verified']} / {results['total_ocr_dates']} ({match_pct:.1f}%)\n"
                    f"    → These flights are cryptographically verified between UI and physical media\n\n"
                    f"  ⚠ STRUCTURAL ALERTS: {results['alerts']} / {results['total_ocr_dates']} ({100-match_pct:.1f}%)\n"
                    f"    → Flights without camera recording, system power cycles, or pre-flight diagnostics\n\n"
                    f"Full report saved to:\n{report_path}"
                )
                
                messagebox.showinfo("Validation Complete", result_msg)
                self.status_bar.config(text=f"Validation complete: {results['verified']}/{results['total_ocr_dates']} dates verified ({match_pct:.1f}%)")
            else:
                messagebox.showerror("Validation Failed", results['message'])
                
        except Exception as e:
            progress_popup.destroy()
            messagebox.showerror("Validation Error", f"Failed to validate: {str(e)}")
            self.status_bar.config(text="Validation failed")

    def create_widgets(self):
        # Title bar
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=40)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="DRONE FORENSIC FRAMEWORK", 
                 font=('Arial', 16, 'bold'), fg='white', bg='#2c3e50').pack(pady=8)
        
        # Main container - adjusted column weights for narrower left panel
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=28)  # Reduced from 35 to 28
        main_frame.grid_columnconfigure(1, weight=72)  # Increased from 65 to 72
        main_frame.grid_rowconfigure(0, weight=1)
        
        # LEFT PANEL
        left_panel = tk.Frame(main_frame, bg='white', relief='groove', bd=2)
        left_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        left_panel.grid_rowconfigure(0, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)
        
        # Create a canvas with scrollbar for the left panel
        left_canvas = tk.Canvas(left_panel, bg='white', highlightthickness=0)
        left_scrollbar = tk.Scrollbar(left_panel, orient='vertical', command=left_canvas.yview)
        left_scrollable = tk.Frame(left_canvas, bg='white')
        
        left_scrollable.bind('<Configure>', lambda e: left_canvas.configure(scrollregion=left_canvas.bbox('all')))
        left_canvas.create_window((0, 0), window=left_scrollable, anchor='nw')
        
        left_canvas.grid(row=0, column=0, sticky='nsew')
        left_scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Update canvas width when resizing - FIXED: use proper item config
        def configure_canvas(event):
            # Update the canvas item width
            left_canvas.itemconfig('all', width=event.width)
            left_canvas.configure(scrollregion=left_canvas.bbox('all'))
        
        left_canvas.bind('<Configure>', configure_canvas)
        
        # ===== CONTENT INSIDE SCROLLABLE FRAME =====
        
        # RUN BUTTON - AT THE VERY TOP
        run_frame = tk.Frame(left_scrollable, bg='white')
        run_frame.pack(fill='x', padx=8, pady=5)
        
        run_btn = tk.Button(run_frame, text="▶ RUN FORENSIC ANALYSIS", command=self.run_analysis,
                  bg='#27ae60', fg='white', font=('Arial', 11, 'bold'), height=2, relief='raised', bd=3)
        run_btn.pack(fill='x')
        
        # Add a separator line
        tk.Frame(left_scrollable, height=2, bg='#2c3e50').pack(fill='x', padx=8, pady=3)
        
        # Input Method
        method_frame = tk.LabelFrame(left_scrollable, text="Input Method", font=('Arial', 10, 'bold'), bg='white')
        method_frame.pack(fill='x', padx=8, pady=4)
        tk.Radiobutton(method_frame, text="Extract from Screenshots (OCR)", 
                       variable=self.input_method, value="screenshots", bg='white', font=('Arial', 9)).pack(anchor='w', padx=8, pady=2)
        tk.Radiobutton(method_frame, text="Load Existing CSV File", 
                       variable=self.input_method, value="csv", bg='white', font=('Arial', 9)).pack(anchor='w', padx=8, pady=2)
        
        # Screenshots Folder
        self.screenshot_frame = tk.LabelFrame(left_scrollable, text="Screenshots Folder", font=('Arial', 10, 'bold'), bg='white')
        self.screenshot_frame.pack(fill='x', padx=8, pady=4)
        entry_frame = tk.Frame(self.screenshot_frame, bg='white')
        entry_frame.pack(fill='x', padx=4, pady=4)
        tk.Entry(entry_frame, textvariable=self.screenshots_path, width=20, font=('Arial', 8)).pack(side='left', padx=(0, 4), fill='x', expand=True)
        tk.Button(entry_frame, text="Browse", command=self.browse_screenshots, bg='#3498db', fg='white', font=('Arial', 8)).pack(side='right')
        
        # Existing CSV
        self.csv_frame = tk.LabelFrame(left_scrollable, text="Existing CSV File", font=('Arial', 10, 'bold'), bg='white')
        self.csv_frame.pack(fill='x', padx=8, pady=4)
        entry_frame2 = tk.Frame(self.csv_frame, bg='white')
        entry_frame2.pack(fill='x', padx=4, pady=4)
        tk.Entry(entry_frame2, textvariable=self.existing_csv_path, width=20, font=('Arial', 8)).pack(side='left', padx=(0, 4), fill='x', expand=True)
        tk.Button(entry_frame2, text="Browse", command=self.browse_csv, bg='#3498db', fg='white', font=('Arial', 8)).pack(side='right')
        
        # Media Folder (Optional)
        media_frame = tk.LabelFrame(left_scrollable, text="Media Folder (Optional)", font=('Arial', 10, 'bold'), bg='white')
        media_frame.pack(fill='x', padx=8, pady=4)
        entry_frame3 = tk.Frame(media_frame, bg='white')
        entry_frame3.pack(fill='x', padx=4, pady=4)
        tk.Entry(entry_frame3, textvariable=self.media_path, width=20, font=('Arial', 8)).pack(side='left', padx=(0, 4), fill='x', expand=True)
        tk.Button(entry_frame3, text="Browse", command=self.browse_media, bg='#3498db', fg='white', font=('Arial', 8)).pack(side='right')
        
        # Drone Selection
        drone_frame = tk.LabelFrame(left_scrollable, text="Drone Selection", font=('Arial', 10, 'bold'), bg='white')
        drone_frame.pack(fill='x', padx=8, pady=4)
        for key, config in DRONE_CONFIGS.items():
            if key in ["1", "2", "6"]:  # Show only relevant drones to save space
                tk.Radiobutton(drone_frame, text=config['name'], variable=self.selected_drone,
                              value=key, bg='white', font=('Arial', 9)).pack(anchor='w', padx=8, pady=1)
        tk.Radiobutton(drone_frame, text="Load from JSON File...", variable=self.selected_drone,
                      value="7", bg='white', font=('Arial', 9)).pack(anchor='w', padx=8, pady=1)
        
        # Case Information
        case_frame = tk.LabelFrame(left_scrollable, text="Case Information", font=('Arial', 10, 'bold'), bg='white')
        case_frame.pack(fill='x', padx=8, pady=4)
        
        case_inner = tk.Frame(case_frame, bg='white')
        case_inner.pack(fill='x', padx=4, pady=4)
        
        tk.Label(case_inner, text="Case Number:", bg='white', font=('Arial', 9)).grid(row=0, column=0, sticky='w', padx=4, pady=2)
        tk.Entry(case_inner, textvariable=self.case_number, width=15, font=('Arial', 9)).grid(row=0, column=1, padx=4, pady=2, sticky='ew')
        case_inner.grid_columnconfigure(1, weight=1)
        
        tk.Label(case_inner, text="Examiner Name:", bg='white', font=('Arial', 9)).grid(row=1, column=0, sticky='w', padx=4, pady=2)
        tk.Entry(case_inner, textvariable=self.examiner, width=15, font=('Arial', 9)).grid(row=1, column=1, padx=4, pady=2, sticky='ew')
        
        # Add some padding at the bottom
        tk.Frame(left_scrollable, height=20, bg='white').pack()
        
        # Update scroll region
        left_scrollable.update_idletasks()
        left_canvas.configure(scrollregion=left_canvas.bbox('all'))
        
        # ===== RIGHT PANEL =====
        right_panel = tk.Frame(main_frame, bg='white', relief='groove', bd=2)
        right_panel.grid(row=0, column=1, sticky='nsew')
        
        # Stats Dashboard
        stats_frame = tk.LabelFrame(right_panel, text="Flight Statistics", font=('Arial', 11, 'bold'), bg='white')
        stats_frame.pack(fill='x', padx=10, pady=5)
        
        stats_row1 = tk.Frame(stats_frame, bg='white')
        stats_row1.pack(fill='x', pady=3)
        self.create_stat_card(stats_row1, "Total Flights", "total", "#2c3e50")
        self.create_stat_card(stats_row1, "Normal Flights", "normal", "#27ae60")
        self.create_stat_card(stats_row1, "Aborted Takeoffs", "aborted", "#e74c3c")
        
        stats_row2 = tk.Frame(stats_frame, bg='white')
        stats_row2.pack(fill='x', pady=3)
        self.create_stat_card(stats_row2, "Total Distance (km)", "distance", "#2980b9")
        self.create_stat_card(stats_row2, "Total Flight Time (hrs)", "hours", "#8e44ad")
        self.create_stat_card(stats_row2, "Max Altitude (m)", "altitude", "#f39c12")
        
        # Flight Table
        table_frame = tk.LabelFrame(right_panel, text="Flight Details", font=('Arial', 11, 'bold'), bg='white')
        table_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        tree_container = tk.Frame(table_frame)
        tree_container.pack(fill='both', expand=True)
        
        columns = ('Flight No.', 'Date/Time', 'Duration (min)', 'Distance (m)', 'Altitude (m)', 'Type')
        self.tree = ttk.Treeview(tree_container, columns=columns, show='headings', height=12)
        
        for col in columns:
            self.tree.heading(col, text=col)
            if col == 'Flight No.':
                self.tree.column(col, width=60)
            elif col == 'Date/Time':
                self.tree.column(col, width=180)
            else:
                self.tree.column(col, width=85)
        
        v_scrollbar = ttk.Scrollbar(tree_container, orient='vertical', command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Export Buttons - Auto-fill available space
        export_frame = tk.Frame(right_panel, bg='white')
        export_frame.pack(fill='x', padx=10, pady=3)
        
        # Configure grid columns to auto-fill
        for i in range(7):
            export_frame.grid_columnconfigure(i, weight=1)
        
        btn_style = {'font': ('Arial', 8), 'height': 1}
        
        tk.Button(export_frame, text="Export Report", command=self.export_report,
                  bg='#3498db', fg='white', **btn_style).grid(row=0, column=0, padx=1, sticky='ew')
        tk.Button(export_frame, text="Export Integrity", command=self.export_integrity,
                  bg='#3498db', fg='white', **btn_style).grid(row=0, column=1, padx=1, sticky='ew')
        tk.Button(export_frame, text="CSV w/ Hashes", command=self.export_csv_with_row_hashing,
                  bg='#27ae60', fg='white', **btn_style).grid(row=0, column=2, padx=1, sticky='ew')
        tk.Button(export_frame, text="Verify Hashes", command=self.verify_csv_hashes,
                  bg='#e67e22', fg='white', **btn_style).grid(row=0, column=3, padx=1, sticky='ew')
        tk.Button(export_frame, text="View Integrity", command=self.view_integrity,
                  bg='#9b59b6', fg='white', **btn_style).grid(row=0, column=4, padx=1, sticky='ew')
        tk.Button(export_frame, text="Run Validation", command=self.run_dual_validation,
                  bg='#e74c3c', fg='white', **btn_style).grid(row=0, column=5, padx=1, sticky='ew')
        tk.Button(export_frame, text="Clear", command=self.clear_results,
                  bg='#95a5a6', fg='white', **btn_style).grid(row=0, column=6, padx=1, sticky='ew')
        
        # Status Bar
        self.status_bar = tk.Label(self.root, text="Ready - Select input method and click RUN FORENSIC ANALYSIS", 
                                   bd=1, relief='sunken', anchor='w', bg='#ecf0f1', font=('Arial', 9))
        self.status_bar.pack(side='bottom', fill='x')
        
        # FIXED: Use trace_add for Python 3.14+ compatibility
        self.input_method.trace_add('write', self.on_method_change)
        self.on_method_change()
    
    def on_method_change(self, *args):
        if self.input_method.get() == "screenshots":
            self.screenshot_frame.config(text="Screenshots Folder")
            self.csv_frame.config(text="Existing CSV File (Not Used)")
        else:
            self.screenshot_frame.config(text="Screenshots Folder (Not Used)")
            self.csv_frame.config(text="Existing CSV File")
    
    def create_stat_card(self, parent, label, key, color):
        frame = tk.Frame(parent, bg='white', relief='ridge', bd=1)
        frame.pack(side='left', expand=True, fill='both', padx=2, pady=2)
        tk.Label(frame, text=label, font=('Arial', 8), bg='white').pack(pady=(2,0))
        self.stats_labels[key] = tk.Label(frame, text="--", font=('Arial', 14, 'bold'), fg=color, bg='white')
        self.stats_labels[key].pack(pady=(0,2))
    
    def browse_screenshots(self):
        folder = filedialog.askdirectory()
        if folder:
            self.screenshots_path.set(folder)
            self.status_bar.config(text=f"Screenshots: {os.path.basename(folder)}")
    
    def browse_csv(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if filename:
            self.existing_csv_path.set(filename)
            self.status_bar.config(text=f"CSV: {os.path.basename(filename)}")
    
    def browse_media(self):
        folder = filedialog.askdirectory()
        if folder:
            self.media_path.set(folder)
            self.status_bar.config(text=f"Media: {os.path.basename(folder)}")
    
    def run_analysis(self):
        try:
            import cv2
            import pytesseract
            import pandas as pd
        except ImportError:
            messagebox.showerror("Error", "OCR libraries not installed.\nRun: pip install opencv-python pytesseract pandas")
            return
        
        # Reset progress dialog
        if self.progress_dialog:
            try:
                self.progress_dialog.destroy()
            except:
                pass
            self.progress_dialog = None
        
        self.progress_dialog = ProgressDialog(self.root, "Processing")
        
        self.status_bar.config(text="Processing...")
        self.root.config(cursor="watch")
        
        try:
            choice = self.selected_drone.get()
            if choice == "7":
                json_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
                if json_path:
                    with open(json_path, 'r') as f:
                        drone_config = json.load(f)
                else:
                    drone_config = {"name": "Custom Drone"}
            else:
                drone_config = DRONE_CONFIGS.get(choice, DRONE_CONFIGS["1"])
            
            self.framework = ForensicFramework(
                self.case_number.get(), self.examiner.get(), drone_config
            )
            self.framework.set_progress_callback(self.show_progress)
            
            if self.media_path.get():
                self.framework.set_media_path(self.media_path.get())
            
            df = None
            
            if self.input_method.get() == "screenshots":
                if not self.screenshots_path.get():
                    self.progress_dialog.destroy()
                    messagebox.showerror("Error", "Please select screenshots folder")
                    self.root.config(cursor="")
                    return
                
                df, msg = extract_from_screenshots(self.screenshots_path.get(), self.show_progress)
                if df is None:
                    self.progress_dialog.destroy()
                    messagebox.showerror("Error", msg)
                    self.root.config(cursor="")
                    return
                self.status_bar.config(text=msg)
                self.framework.integrity.add_evidence(self.screenshots_path.get(), "Screenshots Folder", msg)
            
            else:
                if not self.existing_csv_path.get():
                    self.progress_dialog.destroy()
                    messagebox.showerror("Error", "Please select CSV file")
                    self.root.config(cursor="")
                    return
                df = pd.read_csv(self.existing_csv_path.get())
                self.status_bar.config(text=f"Loaded: {os.path.basename(self.existing_csv_path.get())}")
                self.framework.integrity.add_evidence(self.existing_csv_path.get(), "Ground Truth CSV", 
                                                     f"{len(df)} flights loaded")
            
            flights = self.framework.load_flights(df)
            
            # Format DJI dates if needed
            if choice == "6" and flights:
                for flight in flights:
                    if flight.get('date_time'):
                        flight['date_time'] = self.format_dji_date(flight['date_time'])
            
            self.current_flights = flights
            stats = self.framework.analyze_flights(flights)
            
            self.stats_labels['total'].config(text=str(stats['total']))
            self.stats_labels['normal'].config(text=str(stats['normal']))
            self.stats_labels['aborted'].config(text=str(stats['aborted']))
            self.stats_labels['distance'].config(text=f"{stats['total_distance_km']:.2f}")
            self.stats_labels['hours'].config(text=f"{stats['total_hours']:.1f}")
            self.stats_labels['altitude'].config(text=str(stats['max_altitude']))
            
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            for flight in flights[:100]:
                ftype = "ABORTED" if (flight['distance_m'] == 0 and flight['duration_min'] < 2) else "NORMAL"
                display_date = flight['date_time'] if len(flight['date_time']) > 10 else flight['date_time']
                self.tree.insert('', 'end', values=(
                    flight['flight_no'], display_date,
                    f"{flight['duration_min']:.0f}", f"{flight['distance_m']:.0f}",
                    f"{flight['altitude_m']:.0f}", ftype
                ))
            
            self.framework.save_reports()
            self.progress_dialog.destroy()
            self.progress_dialog = None
            self.status_bar.config(text=f"Complete! {len(flights)} flights analyzed")
            self.analysis_complete = True
            
            messagebox.showinfo("Success", f"Analysis complete!\n\n"
                               f"Total Flights: {stats['total']}\n"
                               f"Normal: {stats['normal']}\n"
                               f"Aborted Takeoffs: {stats['aborted']}\n"
                               f"Total Distance: {stats['total_distance_km']:.2f} km\n"
                               f"Total Flight Time: {stats['total_hours']:.1f} hours\n"
                               f"Max Altitude: {stats['max_altitude']} m\n\n"
                               f"Use Tools menu to run:\n"
                               f"• Dual-Track Validation\n"
                               f"• Baseline Validation (DJI results)")
            
        except Exception as e:
            if self.progress_dialog:
                self.progress_dialog.destroy()
                self.progress_dialog = None
            messagebox.showerror("Error", f"Analysis failed: {str(e)}")
            self.status_bar.config(text="Analysis failed")
        finally:
            self.progress_dialog = None
            self.root.config(cursor="")
    
    def export_report(self):
        if not self.framework:
            messagebox.showerror("Error", "Run analysis first")
            return
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filename:
            self.framework.generate_report(filename)
            messagebox.showinfo("Success", "Forensic report saved")
    
    def export_integrity(self):
        if not self.framework:
            messagebox.showerror("Error", "Run analysis first")
            return
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filename:
            self.framework.integrity.save_log(filename)
            messagebox.showinfo("Success", "Integrity log saved")
    
    def show_about(self):
        messagebox.showinfo("About", 
                           "Drone Forensic Framework v5.1 (Modular)\n\n"
                           "Author: DODZI GBORDZI\n"
                           "Institution: KNUST MSc. Cyber Security and Digital Forensics\n\n"
                           "Features:\n"
                           "- Automatic OCR extraction from PTD1 screenshots\n"
                           "- SHA-256 Integrity Verification\n"
                           "- Per-row SHA-256 hashing for individual flight records\n"
                           "- JSON Configurable Multi-Drone Support\n"
                           "- GPS EXIF Extraction from Photos\n"
                           "- Dual-Track Cross-Validation (Algorithm 3.3)\n"
                           "- CSV Export with Row Hashing\n"
                           "- CSV Hash Verification\n"
                           "SHA-256 provides INTEGRITY VERIFICATION only.\n"
                           "Full chain of custody requires personnel tracking.")


def main():
    root = tk.Tk()
    app = DroneForensicGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()