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
        self.title("AegisGRID Predictive Security Platform v2.1")
        self.geometry("800x650") 
        self.configure(bg="#2E2E2E")
        self.simulation_thread = None
        self.stop_event = threading.Event()
        self.update_queue = queue.Queue()
        self.high_anomaly_var = tk.BooleanVar()

        self._configure_styles()
        self._create_widgets()
        
        self.after(100, self.process_queue)
        self._update_time()
        
        os.makedirs(MODEL_DIR, exist_ok=True)

    def _configure_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        # General styles
        self.style.configure("TFrame", background="#2E2E2E")
        self.style.configure("TLabel", background="#2E2E2E", foreground="white", font=("Segoe UI", 10))
        self.style.configure("TLabelframe", background="#3C3C3C", bordercolor="#555555")
        self.style.configure("TLabelframe.Label", background="#3C3C3C", foreground="white", font=("Segoe UI", 10, "bold"))
        # Header styles
        self.style.configure("Title.TLabel", font=("Segoe UI", 12, "bold"), foreground="#CCCCCC")
        self.style.configure("Time.TLabel", font=("Segoe UI", 10), foreground="#CCCCCC")
        # Dashboard styles
        self.style.configure("Status.TLabel", font=("Segoe UI", 24, "bold"))
        # Progress bar style
        self.style.configure("TProgressbar", troughcolor='#1C1C1C', background='#00BFFF', bordercolor="#1C1C1C")
        # Button styles
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6, borderwidth=0)
        self.style.map("TButton",
            background=[('!disabled', '#4A4A4A'), ('active', '#5A5A5A'), ('disabled', '#3A3A3A')],
            foreground=[('!disabled', 'white'), ('disabled', '#777777')]
        )
        # Checkbox style
        self.style.configure("TCheckbutton", background="#3C3C3C", foreground="white", font=("Segoe UI", 10))
        self.style.map("TCheckbutton",
            indicatorcolor=[('selected', '#00BFFF'), ('!selected', 'white')],
            background=[('active', '#3C3C3C')]
        )

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill="both")

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
            logo_label = ttk.Label(header_frame, image=self.logo_image, style="TLabel")
            logo_label.pack(side="left")
        except Exception as e:
            print(f"Could not load logo image: {e}")
            logo_label = ttk.Label(header_frame, text="🛡️ AegisGRID", font=("Segoe UI Symbol", 24, "bold"), foreground="#00BFFF")
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
        self.log_text = scrolledtext.ScrolledText(log_frame, state="disabled", height=10, bg="#1C1C1C", fg="white", font=("Consolas", 9))
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
