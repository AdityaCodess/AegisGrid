import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time
import os
import sys
from PIL import ImageTk, Image

try:
    from aegis_core.data_simulator import DataSimulator
    from aegis_core.analyzers import ScadaAnalyzer, PmuAnalyzer
    from aegis_core.fusion_center import FusionCenter
    from ui_desktop.components.dashboard import Dashboard 
    from collections import deque
    import pandas as pd
except ImportError as e:
    print(f"--- ImportError --- \nError: {e}")
    sys.exit(1)

# Define file paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MODEL_DIR = os.path.join(ROOT_DIR, 'saved_models')
ASSETS_DIR = os.path.join(ROOT_DIR, 'ui_desktop', 'assets')
LOGO_PATH = os.path.join(ASSETS_DIR, 'logo.png')

SCADA_MODEL_PATH = os.path.join(MODEL_DIR, 'scada_model.joblib')
SCADA_SCALER_PATH = os.path.join(MODEL_DIR, 'scada_scaler.joblib')
PMU_MODEL_PATH = os.path.join(MODEL_DIR, 'pmu_model.h5')
PMU_SCALER_PATH = os.path.join(MODEL_DIR, 'pmu_scaler.joblib')
PMU_THRESHOLD_PATH = os.path.join(MODEL_DIR, 'pmu_threshold.joblib')

class AegisApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AegisGRID Predictive Security Platform v2.2")
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
        
        os.makedirs(MODEL_DIR, exist_ok=True)

    def draw_gradient(self, color1, color2):
        """Draws a vertical gradient on the canvas."""
        self.gradient.delete("gradient")
        width = self.winfo_width()
        height = self.winfo_height()
        r1, g1, b1 = self.winfo_rgb(color1)
        r2, g2, b2 = self.winfo_rgb(color2)
        r_ratio = (r2 - r1) / height
        g_ratio = (g2 - g1) / height
        b_ratio = (b2 - b1) / height

        for i in range(height):
            nr = int(r1 + (r_ratio * i))
            ng = int(g1 + (g_ratio * i))
            nb = int(b1 + (b_ratio * i))
            color = f'#{nr>>8:02x}{ng>>8:02x}{nb>>8:02x}'
            self.gradient.create_line(0, i, width, i, tags=("gradient",), fill=color)

    def on_resize(self, event):
        """Redraws the gradient when the window is resized."""
        self.draw_gradient("#1a202c", "#2d3748")

    def _configure_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        
        # --- FIX 1: Define colors as instance attributes ---
        self.BG_COLOR = "#1a202c"
        self.FRAME_COLOR = "#2d3748"
        self.BORDER_COLOR = "#4a5568"
        self.TEXT_COLOR = "#e2e8f0"
        self.ACCENT_COLOR = "#38b2ac"

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
        self.style.map("TButton",
            background=[('!disabled', self.ACCENT_COLOR), ('active', '#2c7a7b'), ('disabled', '#4a5568')],
            foreground=[('!disabled', 'white'), ('disabled', '#a0aec0')]
        )
        
        self.style.configure("TCheckbutton", background=self.FRAME_COLOR, foreground=self.TEXT_COLOR, font=("Segoe UI", 10))
        self.style.map("TCheckbutton",
            indicatorcolor=[('selected', self.ACCENT_COLOR), ('!selected', 'white')],
            background=[('active', self.FRAME_COLOR)]
        )

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
            img = Image.open(LOGO_PATH)
            max_height = 50
            aspect_ratio = img.width / img.height
            new_width = int(max_height * aspect_ratio)
            img = img.resize((new_width, max_height), Image.Resampling.LANCZOS)
            self.logo_image = ImageTk.PhotoImage(img)
            # --- FIX 2: Use self.BG_COLOR ---
            logo_label = ttk.Label(header_frame, image=self.logo_image, style="TLabel", background=self.BG_COLOR)
            logo_label.pack(side="left")
        except Exception as e:
            print(f"Could not load logo image: {e}")
            # --- FIX 3: Use self.ACCENT_COLOR and self.BG_COLOR ---
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
        self.simulation_thread = threading.Thread(target=self.run_backend_simulation, args=(self.update_queue, self.stop_event, high_anomaly_mode), daemon=True)
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

    @staticmethod
    def run_backend_simulation(update_queue, stop_event, high_anomaly_mode):
        try:
            from tensorflow.keras.losses import MeanSquaredError
            from tensorflow.keras.models import load_model
            import joblib

            update_queue.put("Initializing backend modules...")
            scada_analyzer = ScadaAnalyzer()
            pmu_analyzer = PmuAnalyzer(timesteps=10)
            fusion_center = FusionCenter()
            training_simulator = DataSimulator(high_anomaly_mode=False)

            if os.path.exists(SCADA_MODEL_PATH) and os.path.exists(SCADA_SCALER_PATH):
                update_queue.put("Loading pre-trained SCADA model...")
                scada_analyzer.load_model(SCADA_MODEL_PATH, SCADA_SCALER_PATH)
            else:
                update_queue.put("No pre-trained SCADA model found. Training new model...")
                training_data = [training_simulator.get_data_point() for _ in range(2000)]
                scada_training_data = pd.DataFrame([d['scada'] for d in training_data])
                scada_analyzer.train(scada_training_data)
                update_queue.put("Saving new SCADA model...")
                scada_analyzer.save_model(SCADA_MODEL_PATH, SCADA_SCALER_PATH)

            if all(os.path.exists(p) for p in [PMU_MODEL_PATH, PMU_SCALER_PATH, PMU_THRESHOLD_PATH]):
                update_queue.put("Loading pre-trained PMU model...")
                pmu_analyzer.load_model(PMU_MODEL_PATH, PMU_SCALER_PATH, PMU_THRESHOLD_PATH)
            else:
                update_queue.put("No pre-trained PMU model found. Training new model...")
                training_data = [training_simulator.get_data_point() for _ in range(2000)]
                pmu_training_data = pd.DataFrame([d['pmu'] for d in training_data])
                pmu_analyzer.train(pmu_training_data)
                update_queue.put("Saving new PMU model...")
                pmu_analyzer.save_model(PMU_MODEL_PATH, PMU_SCALER_PATH, PMU_THRESHOLD_PATH)
            
            update_queue.put("Initialization complete. Starting real-time monitoring.")
            live_simulator = DataSimulator(high_anomaly_mode=high_anomaly_mode)
            pmu_history = deque(maxlen=pmu_analyzer.timesteps)
            last_alert_status = False
            while not stop_event.is_set():
                live_data = live_simulator.get_data_point()
                scada_result = scada_analyzer.analyze(live_data['scada'])
                pmu_history.append(live_data['pmu'])
                pmu_result = pmu_analyzer.analyze(list(pmu_history))
                final_alert = fusion_center.fuse(scada_result, pmu_result)
                
                final_alert['location'] = live_data['location']
                final_alert['is_new_alert'] = final_alert['aegis_alert'] and not last_alert_status
                last_alert_status = final_alert['aegis_alert']
                
                update_queue.put(final_alert)
                time.sleep(1)
        except Exception as e:
            import traceback
            update_queue.put(f"Backend Error: {e}\n{traceback.format_exc()}")
        finally:
            update_queue.put("Simulation thread has stopped.")

if __name__ == "__main__":
    app = AegisApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
