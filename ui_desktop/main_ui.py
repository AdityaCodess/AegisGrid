# FILE: ui_desktop/main_ui.py (Updated with Aspect Ratio Fix)
# ===================================================================
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time
import os
import sys

# --- CHANGE 1: Import the Pillow library ---
from PIL import ImageTk, Image

try:
    # Core backend imports
    from aegis_core.data_simulator import DataSimulator
    from aegis_core.analyzers import ScadaAnalyzer, PmuAnalyzer
    from aegis_core.fusion_center import FusionCenter
    # UI component import
    from ui_desktop.components.dashboard import Dashboard 
    from collections import deque
    import pandas as pd
except ImportError as e:
    print(f"--- ImportError --- \nError: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure you are running this script from the project's ROOT directory (the 'aegisgrid' folder).")
    print("   Correct command: python -m ui_desktop.main_ui")
    print("2. Ensure the folder structure is correct (ui_desktop/components/__init__.py must exist).")
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
        self.title("AegisGRID Predictive Security Platform v1.6")
        self.geometry("800x600")
        self.configure(bg="#2E2E2E")

        self.simulation_thread = None
        self.stop_event = threading.Event()
        self.update_queue = queue.Queue()

        self._configure_styles()
        self._create_widgets()
        self.after(100, self.process_queue)
        os.makedirs(MODEL_DIR, exist_ok=True)

    def _configure_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#2E2E2E")
        self.style.configure("TLabel", background="#2E2E2E", foreground="white", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"))
        self.style.configure("Status.TLabel", font=("Segoe UI", 24, "bold"))
        self.style.configure("TButton", font=("Segoe UI", 10), padding=6)
        self.style.map("TButton", background=[('active', '#4A4A4A')], foreground=[('active', 'white')])

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill="both")

        # --- Header with Logo ---
        header_frame = ttk.Frame(main_frame, style="TFrame")
        header_frame.pack(fill="x", pady=(0, 10))
        
        try:
            # Open the image file with Pillow
            img = Image.open(LOGO_PATH)
            
            # --- THE FIX IS HERE: Resize while maintaining aspect ratio ---
            max_height = 50
            original_width, original_height = img.size
            aspect_ratio = original_width / original_height
            new_width = int(max_height * aspect_ratio)
            
            img = img.resize((new_width, max_height), Image.Resampling.LANCZOS)
            
            self.logo_image = ImageTk.PhotoImage(img)
            logo_label = ttk.Label(header_frame, image=self.logo_image, style="TLabel")
            logo_label.pack(side="left")
        except Exception as e:
            # Fallback to text logo if image fails to load for any reason
            print(f"Could not load logo image: {e}")
            logo_label = ttk.Label(header_frame, text="🛡️ AegisGRID", font=("Segoe UI Symbol", 24, "bold"), foreground="#00BFFF")
            logo_label.pack(side="left")

        # --- Dashboard Component ---
        self.dashboard = Dashboard(main_frame)
        self.dashboard.pack(fill="x", pady=10)

        # --- Event Log ---
        log_frame = ttk.Labelframe(main_frame, text="Event Log", padding=10)
        log_frame.pack(pady=10, fill="both", expand=True)
        self.log_text = scrolledtext.ScrolledText(log_frame, state="disabled", height=10, bg="#1C1C1C", fg="white", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

        # --- Control Buttons ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        self.start_button = ttk.Button(button_frame, text="Start Simulation", command=self.start_simulation)
        self.start_button.pack(side="left", padx=10)
        self.stop_button = ttk.Button(button_frame, text="Stop Simulation", command=self.stop_simulation, state="disabled")
        self.stop_button.pack(side="left", padx=10)

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
        self._log_message("Starting simulation thread...")
        self.simulation_thread = threading.Thread(target=self.run_backend_simulation, args=(self.update_queue, self.stop_event), daemon=True)
        self.simulation_thread.start()

    def stop_simulation(self):
        if self.simulation_thread and self.simulation_thread.is_alive():
            self.stop_event.set()
            self._log_message("Stop signal sent to simulation thread.", "WARN")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            
    def process_queue(self):
        try:
            while not self.update_queue.empty():
                message = self.update_queue.get_nowait()
                if isinstance(message, str):
                    self._log_message(message)
                elif isinstance(message, dict):
                    self._update_ui(message)
        finally:
            self.after(200, self.process_queue)

    def _update_ui(self, data):
        self.dashboard.update_display(data)
        if data.get('is_new_alert', False):
            self._log_message(f"ALERT: {data['reason']}", "CRITICAL")

    def on_closing(self):
        self.stop_simulation()
        self.destroy()

    @staticmethod
    def run_backend_simulation(update_queue, stop_event):
        try:
            from tensorflow.keras.losses import MeanSquaredError
            from tensorflow.keras.models import load_model
            import joblib

            update_queue.put("Initializing backend modules...")
            scada_analyzer = ScadaAnalyzer()
            pmu_analyzer = PmuAnalyzer(timesteps=10)
            fusion_center = FusionCenter()

            if os.path.exists(SCADA_MODEL_PATH) and os.path.exists(SCADA_SCALER_PATH):
                update_queue.put("Loading pre-trained SCADA model...")
                scada_analyzer.load_model(SCADA_MODEL_PATH, SCADA_SCALER_PATH)
            else:
                update_queue.put("No pre-trained SCADA model found. Training new model...")
                simulator = DataSimulator()
                training_data = [simulator.get_data_point() for _ in range(2000)]
                scada_training_data = pd.DataFrame([d['scada'] for d in training_data])
                scada_analyzer.train(scada_training_data)
                update_queue.put("Saving new SCADA model...")
                scada_analyzer.save_model(SCADA_MODEL_PATH, SCADA_SCALER_PATH)

            if all(os.path.exists(p) for p in [PMU_MODEL_PATH, PMU_SCALER_PATH, PMU_THRESHOLD_PATH]):
                update_queue.put("Loading pre-trained PMU model...")
                pmu_analyzer.load_model(PMU_MODEL_PATH, PMU_SCALER_PATH, PMU_THRESHOLD_PATH)
            else:
                update_queue.put("No pre-trained PMU model found. Training new model...")
                simulator = DataSimulator()
                training_data = [simulator.get_data_point() for _ in range(2000)]
                pmu_training_data = pd.DataFrame([d['pmu'] for d in training_data])
                pmu_analyzer.train(pmu_training_data)
                update_queue.put("Saving new PMU model...")
                pmu_analyzer.save_model(PMU_MODEL_PATH, PMU_SCALER_PATH, PMU_THRESHOLD_PATH)
            
            update_queue.put("Initialization complete. Starting real-time monitoring.")
            live_simulator = DataSimulator()
            pmu_history = deque(maxlen=pmu_analyzer.timesteps)
            last_alert_status = False
            while not stop_event.is_set():
                live_data = live_simulator.get_data_point()
                scada_result = scada_analyzer.analyze(live_data['scada'])
                pmu_history.append(live_data['pmu'])
                pmu_result = pmu_analyzer.analyze(list(pmu_history))
                final_alert = fusion_center.fuse(scada_result, pmu_result)
                
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
