import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time
import os
import sys
from PIL import ImageTk, Image

try:
    # --- CHANGE: Import the new AegisCore class ---
    from aegis_core.main import AegisCore
    from ui_desktop.components.dashboard import Dashboard 
except ImportError as e:
    print(f"--- ImportError --- \nError: {e}")
    sys.exit(1)

class AegisApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AegisGRID Predictive Security Platform v2.3")
        self.geometry("800x650") 
        
        self.gradient = tk.Canvas(self, highlightthickness=0)
        self.gradient.pack(fill="both", expand=True)
        self.draw_gradient("#1a202c", "#2d3748")
        self.bind("<Configure>", self.on_resize)

        self.simulation_thread = None
        self.stop_event = threading.Event()
        self.update_queue = queue.Queue()
        self.high_anomaly_var = tk.BooleanVar()

        self._configure_styles()
        self._create_widgets()
        
        self.after(100, self.process_queue)
        self._update_time()

    def draw_gradient(self, color1, color2):
        self.gradient.delete("gradient")
        width = self.winfo_width(); height = self.winfo_height()
        r1, g1, b1 = self.winfo_rgb(color1); r2, g2, b2 = self.winfo_rgb(color2)
        r_ratio, g_ratio, b_ratio = (r2 - r1) / height, (g2 - g1) / height, (b2 - b1) / height
        for i in range(height):
            nr, ng, nb = int(r1 + (r_ratio * i)), int(g1 + (g_ratio * i)), int(b1 + (b_ratio * i))
            color = f'#{nr>>8:02x}{ng>>8:02x}{nb>>8:02x}'
            self.gradient.create_line(0, i, width, i, tags=("gradient",), fill=color)

    def on_resize(self, event):
        self.draw_gradient("#1a202c", "#2d3748")

    def _configure_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.BG_COLOR = "#1a202c"; self.FRAME_COLOR = "#2d3748"; self.BORDER_COLOR = "#4a5568"
        self.TEXT_COLOR = "#e2e8f0"; self.ACCENT_COLOR = "#38b2ac"
        self.style.configure(".", background=self.BG_COLOR, foreground=self.TEXT_COLOR)
        self.style.configure("TFrame", background=self.BG_COLOR)
        self.style.configure("App.TFrame", background=self.FRAME_COLOR)
        self.style.configure("TLabel", background=self.FRAME_COLOR, foreground=self.TEXT_COLOR, font=("Segoe UI", 10))
        self.style.configure("TLabelframe", background=self.FRAME_COLOR, bordercolor=self.BORDER_COLOR, relief="solid", borderwidth=1)
        self.style.configure("TLabelframe.Label", background=self.FRAME_COLOR, foreground=self.ACCENT_COLOR, font=("Segoe UI", 11, "bold"))
        self.style.configure("Title.TLabel", background=self.BG_COLOR, font=("Segoe UI", 12, "bold"), foreground="#a0aec0")
        self.style.configure("Time.TLabel", background=self.BG_COLOR, font=("Segoe UI", 10), foreground="#a0aec0")
        self.style.configure("Status.TLabel", background=self.FRAME_COLOR, font=("Segoe UI", 24, "bold"))
        self.style.configure("TProgressbar", troughcolor=self.BG_COLOR, background=self.ACCENT_COLOR, bordercolor=self.BG_COLOR)
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8, borderwidth=0, relief="flat")
        self.style.map("TButton", background=[('!disabled', self.ACCENT_COLOR), ('active', '#2c7a7b'), ('disabled', '#4a5568')], foreground=[('!disabled', 'white'), ('disabled', '#a0aec0')])
        self.style.configure("TCheckbutton", background=self.FRAME_COLOR, foreground=self.TEXT_COLOR, font=("Segoe UI", 10))
        self.style.map("TCheckbutton", indicatorcolor=[('selected', self.ACCENT_COLOR), ('!selected', 'white')], background=[('active', self.FRAME_COLOR)])

    def _create_widgets(self):
        main_frame = ttk.Frame(self.gradient, padding="20", style="TFrame")
        main_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0, relheight=1.0)
        top_header_frame = ttk.Frame(main_frame, style="TFrame")
        top_header_frame.pack(fill="x", pady=(0, 5))
        title_label = ttk.Label(top_header_frame, text="AEGISGRID PLATFORM", style="Title.TLabel")
        title_label.pack(side="left")
        self.time_label = ttk.Label(top_header_frame, text="", style="Time.TLabel")
        self.time_label.pack(side="right")
        header_frame = ttk.Frame(main_frame, style="TFrame")
        header_frame.pack(fill="x", pady=(0, 10))
        try:
            logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo.png')
            img = Image.open(logo_path)
            max_height = 50
            aspect_ratio = img.width / img.height
            new_width = int(max_height * aspect_ratio)
            img = img.resize((new_width, max_height), Image.Resampling.LANCZOS)
            self.logo_image = ImageTk.PhotoImage(img)
            logo_label = ttk.Label(header_frame, image=self.logo_image, style="TLabel", background=self.BG_COLOR)
            logo_label.pack(side="left")
        except Exception as e:
            print(f"Could not load logo image: {e}")
            logo_label = ttk.Label(header_frame, text="🛡️ AegisGRID", font=("Segoe UI Symbol", 24, "bold"), foreground=self.ACCENT_COLOR, background=self.BG_COLOR)
            logo_label.pack(side="left")
        self.dashboard = Dashboard(main_frame)
        self.dashboard.pack(fill="x", pady=10)
        control_frame = ttk.Labelframe(main_frame, text="Controls", padding=10)
        control_frame.pack(pady=10, fill="x")
        self.start_button = ttk.Button(control_frame, text="Start Simulation", command=self.start_simulation)
        self.start_button.pack(side="left", padx=(10,5))
        self.stop_button = ttk.Button(control_frame, text="Stop Simulation", command=self.stop_simulation, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        self.anomaly_check = ttk.Checkbutton(control_frame, text="High Anomaly Mode", variable=self.high_anomaly_var, style="TCheckbutton")
        self.anomaly_check.pack(side="right", padx=10)
        log_frame = ttk.Labelframe(main_frame, text="Event Log", padding=10)
        log_frame.pack(pady=10, fill="both", expand=True)
        self.log_text = scrolledtext.ScrolledText(log_frame, state="disabled", height=10, bg="#0d1117", fg="#c9d1d9", font=("Consolas", 9), relief="flat", borderwidth=0)
        self.log_text.pack(fill="both", expand=True)

    def _update_time(self):
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.after(1000, self._update_time)

    def _log_message(self, message, level="INFO"):
        self.log_text.configure(state="normal")
        log_entry = f"[{time.strftime('%H:%M:%S')}] [{level}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.configure(state="disabled")
        self.log_text.see(tk.END)

    def start_simulation(self):
        self.stop_event.clear()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.anomaly_check.configure(state="disabled")
        high_anomaly_mode = self.high_anomaly_var.get()
        log_mode = "High Anomaly" if high_anomaly_mode else "Normal"
        self._log_message(f"Starting simulation thread in {log_mode} mode...")
        self.simulation_thread = threading.Thread(target=self.run_backend_simulation, args=(high_anomaly_mode,), daemon=True)
        self.simulation_thread.start()

    def stop_simulation(self):
        if self.simulation_thread and self.simulation_thread.is_alive():
            self.stop_event.set()
            self._log_message("Stop signal sent to simulation thread.", "WARN")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.anomaly_check.configure(state="normal")
            
    def process_queue(self):
        try:
            while not self.update_queue.empty():
                message = self.update_queue.get_nowait()
                if isinstance(message, str):
                    self._log_message(message)
                elif isinstance(message, dict):
                    self._update_ui(message)
        finally:
            self.after(100, self.process_queue)

    def _update_ui(self, data):
        self.dashboard.update_display(data)
        if data.get('is_new_alert', False):
            self._log_message(f"ALERT @ {data['location']}: {data['reason']}", "CRITICAL")

    def on_closing(self):
        self.stop_simulation()
        self.destroy()

    def run_backend_simulation(self, high_anomaly_mode):
        """
        This method now simply creates and runs the AegisCore engine.
        """
        try:
            # The callback function will put messages from the core onto the UI's queue
            def ui_callback(message):
                self.update_queue.put(message)

            core_engine = AegisCore(high_anomaly_mode=high_anomaly_mode, update_callback=ui_callback)
            
            # The UI thread now consumes the generator from the core engine
            for status_update in core_engine.run_simulation_generator(self.stop_event):
                self.update_queue.put(status_update)

        except Exception as e:
            import traceback
            self.update_queue.put(f"Backend Error: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    app = AegisApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
