import os
import time
import pandas as pd
from collections import deque

# Use relative imports within the package
from .data_simulator import DataSimulator
from .analyzers import ScadaAnalyzer, PmuAnalyzer
from .fusion_center import FusionCenter

# Define file paths relative to this file's location
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CORE_DIR, '..'))
MODEL_DIR = os.path.join(ROOT_DIR, 'saved_models')

SCADA_MODEL_PATH = os.path.join(MODEL_DIR, 'scada_model.joblib')
SCADA_SCALER_PATH = os.path.join(MODEL_DIR, 'scada_scaler.joblib')
PMU_MODEL_PATH = os.path.join(MODEL_DIR, 'pmu_model.h5')
PMU_SCALER_PATH = os.path.join(MODEL_DIR, 'pmu_scaler.joblib')
PMU_THRESHOLD_PATH = os.path.join(MODEL_DIR, 'pmu_threshold.joblib')

class AegisCore:
    """
    The main backend engine for the AegisGRID platform.
    This class handles all simulation, analysis, and fusion logic.
    """
    def __init__(self, high_anomaly_mode=False, update_callback=None):
        self.high_anomaly_mode = high_anomaly_mode
        self.update_callback = update_callback or (lambda msg: print(msg))

        self.scada_analyzer = ScadaAnalyzer()
        self.pmu_analyzer = PmuAnalyzer(timesteps=10)
        self.fusion_center = FusionCenter()
        
        os.makedirs(MODEL_DIR, exist_ok=True)

    def _initialize_models(self):
        """Loads or trains the AI models."""
        self.update_callback("Initializing backend modules...")

        # --- LOAD OR TRAIN SCADA MODEL ---
        if os.path.exists(SCADA_MODEL_PATH) and os.path.exists(SCADA_SCALER_PATH):
            self.update_callback("Loading pre-trained SCADA model...")
            self.scada_analyzer.load_model(SCADA_MODEL_PATH, SCADA_SCALER_PATH)
        else:
            self.update_callback("No pre-trained SCADA model found. Training new model...")
            training_simulator = DataSimulator(high_anomaly_mode=False)
            training_data = [training_simulator.get_data_point() for _ in range(2000)]
            scada_training_data = pd.DataFrame([d['scada'] for d in training_data])
            self.scada_analyzer.train(scada_training_data)
            self.update_callback("Saving new SCADA model...")
            self.scada_analyzer.save_model(SCADA_MODEL_PATH, SCADA_SCALER_PATH)

        # --- LOAD OR TRAIN PMU MODEL ---
        if all(os.path.exists(p) for p in [PMU_MODEL_PATH, PMU_SCALER_PATH, PMU_THRESHOLD_PATH]):
            self.update_callback("Loading pre-trained PMU model...")
            self.pmu_analyzer.load_model(PMU_MODEL_PATH, PMU_SCALER_PATH, PMU_THRESHOLD_PATH)
        else:
            self.update_callback("No pre-trained PMU model found. Training new model...")
            training_simulator = DataSimulator(high_anomaly_mode=False)
            training_data = [training_simulator.get_data_point() for _ in range(2000)]
            pmu_training_data = pd.DataFrame([d['pmu'] for d in training_data])
            self.pmu_analyzer.train(pmu_training_data)
            self.update_callback("Saving new PMU model...")
            self.pmu_analyzer.save_model(PMU_MODEL_PATH, PMU_SCALER_PATH, PMU_THRESHOLD_PATH)

    def run_simulation_generator(self, stop_event):
        """
        A generator that runs the simulation loop and yields status updates.
        """
        self._initialize_models()
        self.update_callback("Initialization complete. Starting real-time monitoring.")
        
        live_simulator = DataSimulator(high_anomaly_mode=self.high_anomaly_mode)
        pmu_history = deque(maxlen=self.pmu_analyzer.timesteps)
        last_alert_status = False

        while not stop_event.is_set():
            live_data = live_simulator.get_data_point()
            scada_result = self.scada_analyzer.analyze(live_data['scada'])
            pmu_history.append(live_data['pmu'])
            pmu_result = self.pmu_analyzer.analyze(list(pmu_history))
            final_alert = self.fusion_center.fuse(scada_result, pmu_result)
            
            final_alert['location'] = live_data['location']
            final_alert['is_new_alert'] = final_alert['aegis_alert'] and not last_alert_status
            last_alert_status = final_alert['aegis_alert']
            
            yield final_alert # Yield the result dictionary
            time.sleep(1)
        
        self.update_callback("Simulation thread has stopped.")

def run_cli_mode():
    """Function to run the core logic in a command-line interface for testing."""
    print("--- [AegisGRID CLI Test Mode] ---")
    stop_event = threading.Event()
    
    def cli_callback(message):
        if isinstance(message, str):
            print(f"[{time.strftime('%H:%M:%S')}] [SETUP] {message}")

    core = AegisCore(high_anomaly_mode=True, update_callback=cli_callback)
    
    try:
        for status in core.run_simulation_generator(stop_event):
            if status['aegis_alert']:
                print(f"\033[91mALERT! @ {status['location']} | Confidence: {status['combined_confidence']:.0%}\033[0m")
            else:
                print(f"\033[92mSystem Nominal | Confidence: {status['combined_confidence']:.0%}\033[0m")
    except KeyboardInterrupt:
        print("\n--- [Shutdown Signal Received] ---")
        stop_event.set()

if __name__ == "__main__":
    # This allows running `python -m aegis_core.main` for a CLI test
    import threading
    run_cli_mode()