import numpy as np
import time
import random

class DataSimulator:
    """A class to simulate multiple, synchronized data streams from a smart grid."""
    def __init__(self, high_anomaly_mode=False):
        self.timestamp = int(time.time())
        self.locations = [
            'Substation A-1', 'Downtown Sector', 'Industrial Park', 
            'North Residential Grid', 'Airport Feeder Line', 'Hydro Dam Output'
        ]
        self.high_anomaly_mode = high_anomaly_mode
        
        # --- NEW: State variables for sustained anomalies ---
        self.in_anomaly_storm = False
        self.storm_counter = 0
        
        if self.high_anomaly_mode:
            print("Data simulator running in HIGH ANOMALY MODE.")

    def _generate_scada_point(self, is_anomaly=False):
        base_voltage = 230.0; base_current = 50.0; base_frequency = 50.0
        if not is_anomaly:
            voltage = base_voltage + np.random.normal(0, 2)
            current = base_current + np.random.normal(0, 5) * (1 + np.sin(self.timestamp / 60))
            frequency = base_frequency + np.random.normal(0, 0.02)
            breaker_status = 1
        else:
            voltage = base_voltage + np.random.uniform(15, 20)
            current = base_current - np.random.uniform(25, 30)
            frequency = base_frequency + np.random.uniform(0.8, 1.2)
            breaker_status = 1
        return {'voltage': round(voltage, 2), 'current': round(current, 2), 'frequency': round(frequency, 3), 'breaker_status': breaker_status}

    def _generate_pmu_point(self, is_anomaly=False):
        base_phase_angle = 15.0
        if not is_anomaly:
            phase_angle_A = base_phase_angle + np.random.normal(0, 0.1)
            magnitude_A = 1.0 + np.random.normal(0, 0.005)
        else:
            phase_angle_A = base_phase_angle + np.random.uniform(1, 2)
            magnitude_A = 1.0 - np.random.uniform(0.05, 0.1)
        return {'phase_angle_A': round(phase_angle_A, 4), 'magnitude_A': round(magnitude_A, 4)}

    def get_data_point(self):
        """Generates and returns a synchronized data point from all sources."""
        self.timestamp += 1
        is_anomaly_event = False

        if self.high_anomaly_mode:
            # --- NEW: Logic for sustained anomaly "storms" ---
            if self.in_anomaly_storm:
                is_anomaly_event = True
                self.storm_counter -= 1
                if self.storm_counter <= 0:
                    self.in_anomaly_storm = False # End of the storm
            elif random.random() < 0.25: # 25% chance to start a new storm
                self.in_anomaly_storm = True
                self.storm_counter = random.randint(5, 10) # Storm will last 5-10 seconds
                is_anomaly_event = True
        else:
            # Original logic for normal mode
            if random.random() < 0.05:
                is_anomaly_event = True
        
        scada_data = self._generate_scada_point(is_anomaly_event)
        pmu_data = self._generate_pmu_point(is_anomaly_event)

        location = random.choice(self.locations)

        return {
            'timestamp': self.timestamp,
            'is_true_anomaly': is_anomaly_event,
            'location': location,
            'scada': scada_data,
            'pmu': pmu_data
        }
