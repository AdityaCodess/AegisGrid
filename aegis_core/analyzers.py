# FILE: aegis_core/analyzers.py
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Reshape
from tensorflow.keras.losses import MeanSquaredError
import numpy as np
import joblib
import os

class ScadaAnalyzer:
    """Analyzes SCADA data using an Isolation Forest model."""
    def __init__(self):
        self.model = IsolationForest(n_estimators=100, contamination='auto', random_state=42)
        self.scaler = StandardScaler()
        self.features = ['voltage', 'current', 'frequency', 'breaker_status']

    def train(self, historical_data: pd.DataFrame):
        X_train = historical_data[self.features]
        X_train_scaled = self.scaler.fit_transform(X_train)
        self.model.fit(X_train_scaled)

    def analyze(self, data_point: dict):
        df = pd.DataFrame([data_point])
        X_live = df[self.features]
        X_live_scaled = self.scaler.transform(X_live)
        anomaly_score = self.model.score_samples(X_live_scaled)[0]
        normalized_score = 1 - (np.clip(anomaly_score, -1, 0) + 1)
        is_anomaly = self.model.predict(X_live_scaled)[0] == -1
        return {'is_anomaly': is_anomaly, 'confidence': normalized_score}

    def save_model(self, model_path, scaler_path):
        """Saves the trained model and scaler to disk."""
        joblib.dump(self.model, model_path)
        joblib.dump(self.scaler, scaler_path)

    def load_model(self, model_path, scaler_path):
        """Loads the model and scaler from disk."""
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)

class PmuAnalyzer:
    """Analyzes PMU data using an LSTM Autoencoder model."""
    def __init__(self, timesteps=10, n_features=2):
        self.timesteps = timesteps; self.n_features = n_features
        self.features = ['phase_angle_A', 'magnitude_A']
        self.scaler = StandardScaler(); self.model = self._build_model()
        self.reconstruction_threshold = 0.0

    def _build_model(self):
        """Builds the LSTM Autoencoder model."""
        model = Sequential([
            LSTM(32, activation='relu', input_shape=(self.timesteps, self.n_features), return_sequences=True),
            LSTM(16, activation='relu', return_sequences=False),
            Dense(16, activation='relu'),
            Dense(self.timesteps * self.n_features, activation='relu'),
            Reshape((self.timesteps, self.n_features))])
        model.compile(optimizer='adam', loss=MeanSquaredError())
        return model

    def train(self, historical_data: pd.DataFrame):
        scaled_data = self.scaler.fit_transform(historical_data[self.features])
        X_train = []
        for i in range(len(scaled_data) - self.timesteps):
            X_train.append(scaled_data[i:i+self.timesteps])
        X_train = np.array(X_train)
        self.model.fit(X_train, X_train, epochs=20, batch_size=32, verbose=0)
        reconstructions = self.model.predict(X_train, verbose=0)
        train_loss = np.mean(np.mean(np.abs(reconstructions - X_train), axis=1), axis=1)
        self.reconstruction_threshold = np.max(train_loss) * 1.2
        
    def analyze(self, data_sequence: list):
        if len(data_sequence) != self.timesteps: return {'is_anomaly': False, 'confidence': 0.0}
        df = pd.DataFrame(data_sequence)
        scaled_sequence = self.scaler.transform(df[self.features])
        sequence_reshaped = np.array([scaled_sequence])
        reconstruction = self.model.predict(sequence_reshaped, verbose=0)
        reconstruction_error = np.mean(np.abs(reconstruction - sequence_reshaped))
        is_anomaly = reconstruction_error > self.reconstruction_threshold
        confidence = min(reconstruction_error / (self.reconstruction_threshold * 2), 1.0)
        return {'is_anomaly': is_anomaly, 'confidence': confidence}

    def save_model(self, model_path, scaler_path, threshold_path):
        """Saves the trained Keras model, scaler, and threshold."""
        self.model.save(model_path)
        joblib.dump(self.scaler, scaler_path)
        joblib.dump(self.reconstruction_threshold, threshold_path)

    def load_model(self, model_path, scaler_path, threshold_path):
        """Loads the Keras model, scaler, and threshold."""
        # --- THIS IS THE FINAL FIX ---
        # We tell Keras what 'mse' means when loading the model.
        custom_objects = {'mse': MeanSquaredError()}
        self.model = load_model(model_path, custom_objects=custom_objects)
        self.scaler = joblib.load(scaler_path)
        self.reconstruction_threshold = joblib.load(threshold_path)
