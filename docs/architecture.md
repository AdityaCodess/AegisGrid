# 🏛️ AegisGRID Application Architecture

This document provides a high-level overview of the AegisGRID software architecture, its core components, and the flow of data through the system.

---

## 1. High-Level Design Philosophy

The application is designed based on the principle of **Separation of Concerns**. The architecture is split into two primary packages:

1.  **`aegis_core` (The Backend Engine):** This is the "brain" of the application. It is a self-contained Python package responsible for all data simulation, AI analysis, and alert generation. It has no knowledge of the user interface.
2.  **`ui_desktop` (The Frontend Viewer):** This is the graphical user interface (GUI) that the operator interacts with. Its sole purpose is to visualize the data provided by the `aegis_core` engine and to send user commands (like "start" or "stop") back to it.

This separation makes the system modular, easier to debug, and allows either the backend or the frontend to be replaced or upgraded with minimal impact on the other.

---

## 2. Core Components (`aegis_core`)

The backend engine is composed of several specialized modules that work together.

### `data_simulator.py`

- **Purpose:** Acts as a stand-in for a real power grid.
- **Functionality:** Generates a continuous, time-synchronized stream of realistic SCADA and PMU data. It is responsible for injecting anomalies into the data stream to simulate cyber-attacks, with a special "High Anomaly Mode" for demonstration. It also assigns a random grid location to each data point.

### `analyzers.py`

- **Purpose:** Contains the individual AI "detectives" that analyze the data streams.
- **Components:**
  - **`ScadaAnalyzer`:** Uses a Scikit-learn `IsolationForest` model to perform anomaly detection on the lower-frequency SCADA data. It is effective at spotting immediate, out-of-bounds outliers.
  - **`PmuAnalyzer`:** Uses a TensorFlow/Keras `LSTM Autoencoder` model to analyze sequences of high-frequency PMU data. It is designed to detect subtle, time-based patterns and coordinated, stealthy attacks.
- **Persistence:** Both analyzers include methods to save their trained state to disk (`.joblib` or `.h5` files) and load them back, avoiding the need for retraining on every launch.

### `fusion_center.py`

- **Purpose:** Acts as the "control room chief" that makes the final decision.
- **Functionality:** Receives the analytical results (anomaly status and confidence scores) from both the SCADA and PMU analyzers. It uses a weighted logic to "fuse" these inputs into a single, high-confidence **Aegis Alert**. This is the key to reducing false positives.

### `main.py`

- **Purpose:** The main orchestrator for the entire backend engine.
- **Functionality:** Contains the `AegisCore` class, which manages the complete simulation lifecycle. When run, it initializes the models (training or loading), starts the data simulator, passes data to the analyzers, and sends the final fused alert to the UI via a callback system. It also includes a command-line interface (CLI) mode for testing the backend independently of the UI.

---

## 3. User Interface (`ui_desktop`)

The user interface is the visual layer of the platform.

### `main_ui.py`

- **Purpose:** The main application window and controller.
- **Functionality:** Responsible for building the main window, header, logo, control panel, and event log. It creates and manages the separate thread for the `AegisCore` engine. It uses a queue to receive status updates from the backend and passes them to the dashboard for display.

### `components/dashboard.py`

- **Purpose:** A self-contained, reusable UI component for displaying real-time status.
- **Functionality:** Contains all the primary display widgets: the main "AEGIS ALERT" status, the threat confidence bar, the location of interest, and the individual analyzer statuses. It includes animation logic (like the pulsing alert) to make the display more dynamic and engaging.

---

## 4. Data Flow Diagram

The flow of information through the application follows a clear, one-way path during each cycle.

```
[ui_desktop/main_ui.py]
      |
      | (User clicks "Start")
      V
[aegis_core/main.py: AegisCore]
      |
      | 1. Initializes/Loads Models
      | 2. Starts Simulation Loop...
      |
      V
[aegis_core/data_simulator.py] -> Generates (SCADA + PMU Data Point)
      |
      |----------------------------------------------------|
      |                                                    |
      V                                                    V
[aegis_core/analyzers.py: ScadaAnalyzer]         [aegis_core/analyzers.py: PmuAnalyzer]
      |                                                    |
      | -> Analyzes SCADA data                             | -> Analyzes PMU data sequence
      | -> Result 1 (e.g., Anomaly=False)                  | -> Result 2 (e.g., Anomaly=True)
      |                                                    |
      |------------------------|---------------------------|
                               |
                               V
                [aegis_core/fusion_center.py]
                               |
                               | -> Fuses Result 1 & 2
                               | -> Generates Final Aegis Alert
                               |
                               V
[aegis_core/main.py: AegisCore] -> Yields Final Alert
      |
      | (Callback via Queue)
      V
[ui_desktop/main_ui.py] -> Receives Alert -> Updates UI
```
