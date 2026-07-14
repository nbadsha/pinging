import sys
import os
import subprocess
import threading
import time
import re
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import csv
import traceback

# Default devices
DEVICES = [
    {"name": "Bhatar", "ip": "10.13.12.1"},
    {"name": "Home", "ip": "192.168.0.1"},
    {"name": "OMNI", "ip": "192.168.0.20"},
    {"name": "PRO", "ip": "192.168.0.94"},
    {"name": "5G AP", "ip": "192.168.0.95"},
    {"name": "5G Station", "ip": "192.168.0.96"},
    {"name": "ALPHA", "ip": "192.168.0.97"},
    {"name": "CHARLIE", "ip": "192.168.0.99"},
    {"name": "SUROJ SHOP", "ip": "192.168.0.37"},
    {"name": "SUROJ HOME", "ip": "192.168.0.37"},
    {"name": "MITHUN HOME", "ip": "192.168.0.44"},
    {"name": "LADIN", "ip": "192.168.0.44"},
]

# Simple color map for small dot icons used in the tab bar.
# We generate actual image objects at runtime (Pillow preferred, Tk fallback)
DOT_COLORS = {
    "gray": "#808080",
    "green": "#00C800",
    "yellow": "#FFCC00",
    "orange": "#FF8800",
    "red": "#FF4444",
}

class AddDeviceDialog(simpledialog.Dialog):
    def __init__(self, parent, title):
        self.name_result = None
        self.ip_result = None
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="Device Name:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_name = ttk.Entry(master, width=30)
        self.entry_name.grid(row=0, column=1, padx=5, pady=5)
        self.entry_name.focus_set()

        ttk.Label(master, text="IP Address:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.entry_ip = ttk.Entry(master, width=30)
        self.entry_ip.grid(row=1, column=1, padx=5, pady=5)

        return self.entry_name

    def validate(self):
        name = self.entry_name.get().strip()
        ip = self.entry_ip.get().strip()
        if not name:
            messagebox.showwarning("Validation Error", "Please enter a device name.")
            return False
        ip_pattern = r"^([a-zA-Z0-9\-]+\.)*[a-zA-Z0-9\-]+$|^[0-9\.]+$"
        if not ip or not re.match(ip_pattern, ip):
            messagebox.showwarning("Validation Error", "Please enter a valid IP/Domain.")
            return False
        self.name_result = name
        self.ip_result = ip
        return True

    def apply(self):
        pass


class PingTab(ttk.Frame):
    def __init__(self, parent, name, ip, app_instance):
        super().__init__(parent)
        self.name = name
        self.ip = ip
        self.app = app_instance
        self.is_running = False
        self.ping_thread = None
        
        self.sent = 0
        self.received = 0
        self.lost = 0
        self.min_ping = float('inf')
        self.max_ping = 0.0
        
        self.setup_ui()
        self.start_ping()

    def setup_ui(self):
        top_panel = ttk.LabelFrame(self, text=f" Info: {self.name} ({self.ip}) ")
        top_panel.pack(fill=tk.X, padx=10, pady=5)
        
        self.stats_var = tk.StringVar(value="Sent: 0  |  Received: 0  |  Lost: 0  |  Loss: 0.0%  |  Min: -- ms  |  Max: -- ms")
        lbl_stats = ttk.Label(top_panel, textvariable=self.stats_var, font=("Consolas", 10, "bold"))
        lbl_stats.pack(side=tk.LEFT, padx=15, pady=10)
        
        self.btn_toggle = ttk.Button(top_panel, text="Stop", command=self.toggle_ping, width=10)
        self.btn_toggle.pack(side=tk.RIGHT, padx=10, pady=10)
        
        console_frame = ttk.Frame(self)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.console = scrolledtext.ScrolledText(
            console_frame, wrap=tk.WORD, bg="#1e1e1e", fg="#00ff00", insertbackground="white", font=("Consolas", 10)
        )
        self.console.pack(fill=tk.BOTH, expand=True)
        self.console.insert(tk.END, f"--- Starting Ping Monitor for {self.name} ({self.ip}) ---\n")

    def toggle_ping(self):
        if self.is_running:
            self.stop_ping()
        else:
            self.start_ping()

    def start_ping(self):
        self.is_running = True
        self.btn_toggle.config(text="Stop")
        self.ping_thread = threading.Thread(target=self.ping_worker, daemon=True)
        self.ping_thread.start()

    def stop_ping(self):
        self.is_running = False
        self.btn_toggle.config(text="Start")
        self.update_status_light(None, is_lost=False, stopped=True)
        self.write_to_console("\n--- Ping stopped by user ---\n")

    def write_to_console(self, text):
        self.console.insert(tk.END, text)
        self.console.see(tk.END)

    def update_stats_ui(self):
        loss_pct = (self.lost / self.sent * 100) if self.sent > 0 else 0.0
        min_str = f"{self.min_ping:.1f}" if self.min_ping != float('inf') else "--"
        max_str = f"{self.max_ping:.1f}" if self.max_ping > 0 else "--"
        
        self.stats_var.set(
            f"Sent: {self.sent}  |  Received: {self.received}  |  Lost: {self.lost}  |  "
            f"Loss: {loss_pct:.1f}%  |  Min: {min_str} ms  |  Max: {max_str} ms"
        )

    def update_status_light(self, latency, is_lost=False, stopped=False):
        if stopped:
            color_key = "gray"
        elif is_lost or latency is None:
            color_key = "red"
        elif latency <= 100:
            color_key = "green"
        elif latency <= 500:
            color_key = "yellow"
        elif latency <= 1000:
            color_key = "orange"
        else:
            color_key = "red"
            
        # Update this specific tab header indicator light directly via safety thread queue
        self.app.update_tab_icon(self, color_key)

    def extract_latency(self, text):
        match = re.search(r"time[=<]\s*([\d\.]+)\s*ms", text, re.IGNORECASE)
        if match:
            try: return float(match.group(1))
            except ValueError: return None
        return None

    def ping_worker(self):
        cmd = ["ping", "-n", "1", "-w", "1000", self.ip] if os.name == "nt" else ["ping", "-c", "1", "-W", "1", self.ip]
        while self.is_running:
            self.sent += 1
            try:
                startupinfo = None
                if os.name == "nt":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=startupinfo, timeout=2)
                output = result.stdout
                is_lost = False
                
                if result.returncode != 0 or "timed out" in output.lower() or "unreachable" in output.lower():
                    is_lost = True
                
                if is_lost:
                    self.lost += 1
                    self.write_to_console(f"Request timed out (Ping to {self.ip} failed).\n")
                    self.update_status_light(None, is_lost=True)
                else:
                    self.received += 1
                    lines = output.splitlines()
                    important_line = ""
                    for line in lines:
                        if "reply from" in line.lower() or "bytes from" in line.lower():
                            important_line = line
                            break
                    if not important_line and len(lines) > 1:
                        important_line = lines[1]
                        
                    self.write_to_console(important_line + "\n")
                    latency = self.extract_latency(important_line)
                    self.update_status_light(latency, is_lost=False)
                    
                    if latency is not None:
                        if latency < self.min_ping: self.min_ping = latency
                        if latency > self.max_ping: self.max_ping = latency
            except Exception as e:
                self.lost += 1
                self.write_to_console(f"Error pinging {self.ip}: {str(e)}\n")
                self.update_status_light(None, is_lost=True)
            
            self.update_stats_ui()
            time.sleep(1)


class PingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Multi-Ping Console Dashboard")
        self.geometry("1000x615")
        
        # Initialize the global photo image references inside main thread memory
        self.dot_images = {}
        for k, color in DOT_COLORS.items():
            # Try to generate a small circular dot image (preferred: Pillow)
            try:
                from PIL import Image, ImageDraw, ImageTk
                size = (16, 16)
                pil = Image.new("RGBA", size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(pil)
                draw.ellipse((2, 2, size[0]-3, size[1]-3), fill=color)
                self.dot_images[k] = ImageTk.PhotoImage(pil)
            except Exception:
                # Pillow missing or failed; fallback to a solid square Tk PhotoImage
                try:
                    img = tk.PhotoImage(width=8, height=8)
                    # fill with color using put; PhotoImage expects color names or #RRGGBB
                    pixels = [[color]*8 for _ in range(8)]
                    img.put(pixels)
                    self.dot_images[k] = img
                except Exception:
                    print("Failed to create fallback dot image for:", k)
                    traceback.print_exc()
                    self.dot_images[k] = None
        
        # Setup Theme Styles
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Configure tabs to display image icons cleanly stacked on top of the text label
        self.style.configure("TNotebook", background="#2d2d2d", borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#404040", foreground="white", 
                             padding=[12, 6], font=("Segoe UI", 9), compound="top")
        self.style.map("TNotebook.Tab", background=[("selected", "#1e1e1e")], foreground=[("selected", "#00ff00")])
        
        # Top Global Toolbar Frame
        toolbar = ttk.Frame(self, padding=5)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        
        lbl_title = ttk.Label(toolbar, text="Network Performance Dashboard", font=("Segoe UI", 12, "bold"))
        lbl_title.pack(side=tk.LEFT, padx=5)
        
        btn_download = ttk.Button(toolbar, text="📥 Download Stats (CSV)", command=self.download_all_stats)
        btn_download.pack(side=tk.RIGHT, padx=5)
        
        # Notebook Layout
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tabs = []
        for dev in DEVICES:
            tab = PingTab(self.notebook, dev["name"], dev["ip"], self)
            self.notebook.add(tab, text=f"{dev['name']}", image=self.dot_images["gray"])
            self.tabs.append(tab)
            
        # "+" Configuration Tab Setup
        self.add_button_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.add_button_frame, text="  +  ")
        
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def update_tab_icon(self, tab_instance, color_key):
        """Safely modifies individual tab headers with matching color indicators across runtime threads"""
        try:
            index = self.notebook.index(tab_instance)
            self.notebook.tab(index, image=self.dot_images[color_key])
        except Exception:
            pass

    def create_new_device_tab(self, name, ip):
        self.notebook.forget(self.add_button_frame)
        tab = PingTab(self.notebook, name, ip, self)
        self.tabs.append(tab)
        self.notebook.add(tab, text=f"{name}", image=self.dot_images["gray"])
        self.notebook.add(self.add_button_frame, text="  +  ")
        return tab

    def on_tab_changed(self, event):
        selected_tab = self.notebook.select()
        if not selected_tab: return
            
        active_widget = self.notebook.nametowidget(selected_tab)
        if active_widget == self.add_button_frame:
            dialog = AddDeviceDialog(self, "Add New Ping Target")
            if dialog.name_result and dialog.ip_result:
                new_tab = self.create_new_device_tab(dialog.name_result, dialog.ip_result)
                self.notebook.select(new_tab)
            else:
                if self.tabs: self.notebook.select(self.tabs[-1])

    def download_all_stats(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")], title="Save Ping Statistics"
        )
        if not file_path: return
            
        try:
            with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Device Name", "IP Address", "Packets Sent", "Packets Received", "Packets Lost", "Loss %", "Min Latency (ms)", "Max Latency (ms)"])
                for tab in self.tabs:
                    loss_pct = (tab.lost / tab.sent * 100) if tab.sent > 0 else 0.0
                    min_val = f"{tab.min_ping:.2f}" if tab.min_ping != float('inf') else "N/A"
                    max_val = f"{tab.max_ping:.2f}" if tab.max_ping > 0 else "N/A"
                    writer.writerow([tab.name, tab.ip, tab.sent, tab.received, tab.lost, f"{loss_pct:.1f}%", min_val, max_val])
                    
            messagebox.showinfo("Success", f"Statistics successfully exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save file:\n{str(e)}")


if __name__ == "__main__":
    app = PingApp()
    app.mainloop()