# ===================================================================
# FILE: ui_desktop/main_ui.py 
# ===================================================================
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time
import os
import sys

try:
    from aegis_core.data_simulator import DataSimulator
    from aegis_core.analyzers import ScadaAnalyzer, PmuAnalyzer
    from aegis_core.fusion_center import FusionCenter
    from collections import deque
    import pandas as pd
except ImportError as e:
    print(f"--- ImportError --- \nError: {e}")
    sys.exit(1)

# Define file paths for saved models
MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'saved_models'))
SCADA_MODEL_PATH = os.path.join(MODEL_DIR, 'scada_model.joblib')
SCADA_SCALER_PATH = os.path.join(MODEL_DIR, 'scada_scaler.joblib')
PMU_MODEL_PATH = os.path.join(MODEL_DIR, 'pmu_model.h5')
PMU_SCALER_PATH = os.path.join(MODEL_DIR, 'pmu_scaler.joblib')
PMU_THRESHOLD_PATH = os.path.join(MODEL_DIR, 'pmu_threshold.joblib')

class AegisApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AegisGRID Predictive Security Platform v1.0")
        self.geometry("800x600")
        self.configure(bg="#2E2E2E")
        self.simulation_thread = None
        self.stop_event = threading.Event()
        self.update_queue = queue.Queue()
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#2E2E2E")
        self.style.configure("TLabel", background="#2E2E2E", foreground="white", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"))
        self.style.configure("Status.TLabel", font=("Segoe UI", 24, "bold"))
        self.style.configure("TButton", font=("Segoe UI", 10), padding=6)
        self.style.map("TButton", background=[('active', '#4A4A4A')], foreground=[('active', 'white')])
        self._create_widgets()
        self.after(100, self.process_queue)
        # Ensure model directory exists
        os.makedirs(MODEL_DIR, exist_ok=True)

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill="both")
        header_label = ttk.Label(main_frame, text="AegisGRID Real-Time Monitoring", style="Header.TLabel")
        header_label.pack(pady=(0, 20))
        status_frame = ttk.Frame(main_frame, style="TFrame")
        status_frame.pack(fill="x", pady=10)
        self.status_label = ttk.Label(status_frame, text="STANDBY", style="Status.TLabel", foreground="#FFA500")
        self.status_label.pack()
        self.reason_label = ttk.Label(status_frame, text="Simulation not started.", style="TLabel")
        self.reason_label.pack(pady=5)
        confidence_frame = ttk.Frame(main_frame)
        confidence_frame.pack(pady=10)
        ttk.Label(confidence_frame, text="Threat Confidence:", style="TLabel").pack(side="left", padx=5)
        self.confidence_progress = ttk.Progressbar(confidence_frame, orient="horizontal", length=300, mode="determinate")
        self.confidence_progress.pack(side="left")
        self.confidence_label = ttk.Label(confidence_frame, text="0%", style="TLabel", width=5)
        self.confidence_label.pack(side="left", padx=5)
        analyzer_frame = ttk.Frame(main_frame)
        analyzer_frame.pack(pady=20, fill="x", expand=True)
        analyzer_frame.columnconfigure((0, 1), weight=1)
        scada_frame = ttk.Labelframe(analyzer_frame, text="SCADA Analyzer", padding=10)
        scada_frame.grid(row=0, column=0, sticky="ew", padx=10)
        self.scada_status_label = ttk.Label(scada_frame, text="Status: N/A", font=("Segoe UI", 12))
        self.scada_status_label.pack()
        pmu_frame = ttk.Labelframe(analyzer_frame, text="PMU Analyzer", padding=10)
        pmu_frame.grid(row=0, column=1, sticky="ew", padx=10)
        self.pmu_status_label = ttk.Label(pmu_frame, text="Status: N/A", font=("Segoe UI", 12))
        self.pmu_status_label.pack()
        log_frame = ttk.Labelframe(main_frame, text="Event Log", padding=10)
        log_frame.pack(pady=10, fill="both", expand=True)
        self.log_text = scrolledtext.ScrolledText(log_frame, state="disabled", height=10, bg="#1C1C1C", fg="white", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)
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
        if data['aegis_alert']:
            self.status_label.config(text="AEGIS ALERT", foreground="#FF4B4B")
            if data.get('is_new_alert', False): # Log only new alerts
                self._log_message(f"ALERT: {data['reason']}", "CRITICAL")
        else:
            self.status_label.config(text="SYSTEM NOMINAL", foreground="#76FF03")
        self.reason_label.config(text=data['reason'])
        confidence_percent = data['combined_confidence'] * 100
        self.confidence_progress['value'] = confidence_percent
        self.confidence_label.config(text=f"{confidence_percent:.0f}%")
        scada_color = "#FFD700" if data['scada_anomaly'] else "white"
        self.scada_status_label.config(text=f"Status: {'ANOMALY' if data['scada_anomaly'] else 'Normal'}", foreground=scada_color)
        pmu_color = "#FFD700" if data['pmu_anomaly'] else "white"
        self.pmu_status_label.config(text=f"Status: {'ANOMALY' if data['pmu_anomaly'] else 'Normal'}", foreground=pmu_color)

    def on_closing(self):
        self.stop_simulation()
        self.destroy()

    @staticmethod
    def run_backend_simulation(update_queue, stop_event):
        try:
            update_queue.put("Initializing backend modules...")
            scada_analyzer = ScadaAnalyzer()
            pmu_analyzer = PmuAnalyzer(timesteps=10)
            fusion_center = FusionCenter()

            # --- LOAD OR TRAIN SCADA MODEL ---
            if os.path.exists(SCADA_MODEL_PATH) and os.path.exists(SCADA_SCALER_PATH):
                update_queue.put("Loading pre-trained SCADA model...")
                scada_analyzer.load_model(SCADA_MODEL_PATH, SCADA_SCALER_PATH)
            else:
                update_queue.put("No pre-trained SCADA model found. Training new model...")
                simulator = DataSimulator()
                num_training_points = 2000
                training_data = [simulator.get_data_point() for _ in range(num_training_points)]
                scada_training_data = pd.DataFrame([d['scada'] for d in training_data])
                scada_analyzer.train(scada_training_data)
                update_queue.put("Saving new SCADA model...")
                scada_analyzer.save_model(SCADA_MODEL_PATH, SCADA_SCALER_PATH)

            # --- LOAD OR TRAIN PMU MODEL ---
            if all(os.path.exists(p) for p in [PMU_MODEL_PATH, PMU_SCALER_PATH, PMU_THRESHOLD_PATH]):
                update_queue.put("Loading pre-trained PMU model...")
                pmu_analyzer.load_model(PMU_MODEL_PATH, PMU_SCALER_PATH, PMU_THRESHOLD_PATH)
            else:
                update_queue.put("No pre-trained PMU model found. Training new model...")
                simulator = DataSimulator()
                num_training_points = 2000
                training_data = [simulator.get_data_point() for _ in range(num_training_points)]
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
            update_queue.put(f"Backend Error: {e}")
        finally:
            update_queue.put("Simulation thread has stopped.")

if __name__ == "__main__":
    app = AegisApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
