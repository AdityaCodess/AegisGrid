# FILE: aegis_core/fusion_center.py
class FusionCenter:
    def __init__(self, scada_weight=0.6, pmu_weight=0.4):
        self.scada_weight = scada_weight
        self.pmu_weight = pmu_weight
        self.alert_threshold = 0.7
    def fuse(self, scada_result: dict, pmu_result: dict):
        combined_confidence = (scada_result['confidence'] * self.scada_weight + pmu_result['confidence'] * self.pmu_weight)
        if scada_result['is_anomaly'] and pmu_result['is_anomaly']:
            combined_confidence = min(combined_confidence * 1.5, 1.0)
            reason = "Coordinated anomaly detected in both SCADA and PMU data streams."
        elif scada_result['is_anomaly']:
            reason = "Anomaly detected in SCADA data."
        elif pmu_result['is_anomaly']:
            reason = "Anomaly detected in PMU data stream."
        else:
            reason = "System nominal."
        is_aegis_alert = combined_confidence > self.alert_threshold
        return {'aegis_alert': is_aegis_alert, 'combined_confidence': round(combined_confidence, 2), 'reason': reason, 'scada_anomaly': scada_result['is_anomaly'], 'pmu_anomaly': pmu_result['is_anomaly']}