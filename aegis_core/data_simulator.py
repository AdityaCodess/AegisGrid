# FILE: aegis_core/data_simulator.py
import numpy as np
import time

class DataSimulator:
    def __init__(self):
        self.timestamp = int(time.time())
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
        self.timestamp += 1
        is_anomaly_event = np.random.rand() < 0.05
        scada_data = self._generate_scada_point(is_anomaly_event)
        pmu_data = self._generate_pmu_point(is_anomaly_event)
        return {'timestamp': self.timestamp, 'is_true_anomaly': is_anomaly_event, 'scada': scada_data, 'pmu': pmu_data}