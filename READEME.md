# 🛡️ AegisGRID: Predictive Security Platform for Smart Grids

AegisGRID is a desktop application that simulates a next-generation cybersecurity system for power grids. It uses a multi-layered AI engine to predict and detect cyber-attacks in real-time, moving beyond simple alarms to provide proactive threat analysis.

The core idea is to function like a **weather forecast for blackouts**. Instead of only reporting a problem when it's already happening, AegisGRID analyzes multiple data streams to find the warning signs of an attack—like dark clouds and rising wind before a storm—giving operators the crucial time needed to prevent a crisis before it begins.

---

## ✨ Core Features

- **Dual AI Analyzers:** Utilizes two distinct AI models working in parallel:
  - **SCADA Analyzer (Isolation Forest):** Detects immediate, obvious anomalies in operational data (voltage, current, etc.).
  - **PMU Analyzer (LSTM Autoencoder):** Detects subtle, stealthy patterns in high-resolution time-series data that indicate a coordinated attack.
- **Intelligent Fusion Center:** A central logic core that correlates alerts from both analyzers. It intelligently weighs the evidence to produce a single, high-confidence "Aegis Alert," dramatically reducing false positives.
- **Real-Time Dashboard UI:** A user-friendly desktop application built with Tkinter that provides at-a-glance situational awareness, including overall system status, threat confidence levels, and individual analyzer states.
- **Location Tracking:** Pinpoints the specific sector of the grid where a detected anomaly is occurring, providing actionable intelligence to operators.
- **Model Persistence:** The application intelligently saves its trained AI models. The first run performs a one-time training, while subsequent runs load the saved models for an instant start-up.
- **Multi-threaded Architecture:** The backend AI engine runs in a separate thread from the UI, ensuring the dashboard remains smooth and responsive at all times.

---

## 🚀 Project Vision (Future Features)

This prototype lays the foundation for a full-scale security suite. The planned next steps include:

- **Threat Classification:** Evolving from "Anomaly Detected" to classifying the specific type of attack (e.g., "False Data Injection," "DDoS").
- **Attack Vector Visualization:** Displaying a real-time map of the grid that visually highlights the compromised components and the likely path of the attack.
- **The "Resilience Playbook":** An AI-driven recommendation engine that suggests specific, actionable steps for operators to take in response to a detected threat.

---

## 💻 Technology Stack

- **Backend & AI:** Python
- **Machine Learning:** Scikit-learn (for Isolation Forest)
- **Deep Learning:** TensorFlow / Keras (for LSTM Autoencoder)
- **Desktop UI:** Tkinter, Pillow (for image handling)
- **Data Handling:** Pandas, NumPy
- **Model Persistence:** Joblib

---

## 📂 Project Structure

```
aegisgrid/
├── aegis_core/
│   ├── __init__.py
│   ├── analyzers.py
│   ├── data_simulator.py
│   ├── fusion_center.py
│   └── main.py
├── ui_desktop/
│   ├── __init__.py
│   ├── main_ui.py
│   ├── assets/
│   │   └── logo.png
│   └── components/
│       ├── __init__.py
│       └── dashboard.py
├── saved_models/
│   └── (Models are saved here after first run)
├── requirements.txt
└── README.md
```

---

## 🛠️ Setup and Installation

Follow these steps to get the AegisGRID application running on your local machine.

### 1. Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### 2. Clone the Repository (or download the source code)

```bash
git clone [https://github.com/AdityaCodess/AegisGrid.git](https://github.com/AdityaCodess/AegisGrid.git)
cd aegisgrid
```

### 3. Install Dependencies

Install all the required Python libraries using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

_(Note: If you don't have a `requirements.txt` file, you can install the packages manually: `pip install pandas numpy scikit-learn tensorflow Pillow joblib`)_

---

## ▶️ How to Run the Application

The application **must** be run from the root directory of the project (`aegisgrid/`).

1.  Open your terminal or command prompt.
2.  Navigate to the root `aegisgrid` folder.
3.  Run the following command:

```bash
python -m ui_desktop.main_ui
```

### Expected Behavior:

- **First Run:** The application window will appear, and the event log will show messages like "No pre-trained model found. Training new model...". This process will take 20-30 seconds. Afterwards, the simulation will begin. The trained models will be saved in the `saved_models/` folder.
- **Subsequent Runs:** When you run the app again, the log will show "Loading pre-trained model...", and the simulation will start almost instantly.
