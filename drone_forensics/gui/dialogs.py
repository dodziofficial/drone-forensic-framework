"""Dialog windows for the Drone Forensic Framework GUI"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime


class ProgressDialog:
    """Progress bar dialog for long operations"""
    def __init__(self, parent, title="Processing"):
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("450x160")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Remove the X button completely - user cannot close
        self.window.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Center the window over the parent
        self.window.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (450 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (160 // 2)
        self.window.geometry(f"+{x}+{y}")
        
        tk.Label(self.window, text="Running Forensic Analysis", font=('Arial', 12, 'bold')).pack(pady=10)
        
        self.progress_bar = ttk.Progressbar(self.window, length=350, mode='determinate', maximum=100)
        self.progress_bar.pack(pady=10)
        self.progress_bar['value'] = 0
        
        self.progress_label = tk.Label(self.window, text="Starting... (0%)")
        self.progress_label.pack(pady=5)
    
    def update(self, percent, message):
        self.progress_bar['value'] = percent
        self.progress_label.config(text=f"{message}... ({percent}%)")
        self.window.update_idletasks()
    
    def destroy(self):
        self.window.destroy()


def show_manual_dialog(parent, manual_content):
    """Display the framework manual in a scrollable window"""
    popup = tk.Toplevel(parent)
    popup.title("Drone Forensic Framework - User Manual")
    popup.geometry("950x800")
    popup.configure(bg='#f0f0f0')
    
    text_frame = tk.Frame(popup, bg='#f0f0f0')
    text_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    text_widget = scrolledtext.ScrolledText(
        text_frame, 
        wrap=tk.WORD, 
        font=('Consolas', 12),
        bg='white',
        fg='#2c3e50',
        spacing1=2,
        spacing2=1
    )
    text_widget.pack(fill='both', expand=True)
    text_widget.insert('1.0', manual_content)
    text_widget.config(state='disabled')
    
    button_frame = tk.Frame(popup, bg='#f0f0f0')
    button_frame.pack(pady=10)
    
    def save_manual_to_file():
        try:
            filename = f"drone_forensic_manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(manual_content)
            messagebox.showinfo("Manual Saved", f"Manual saved to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save manual: {str(e)}")
    
    tk.Button(button_frame, text="Save Manual to File", command=save_manual_to_file,
              bg='#27ae60', fg='white', font=('Arial', 11, 'bold'), padx=15, pady=8).pack(side='left', padx=10)
    tk.Button(button_frame, text="Close Manual", command=popup.destroy,
              bg='#e74c3c', fg='white', font=('Arial', 11, 'bold'), padx=20, pady=8).pack(side='left', padx=10)