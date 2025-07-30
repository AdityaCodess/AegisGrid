# FILE: ui_desktop/components/dashboard.py
import tkinter as tk
from tkinter import ttk

class Dashboard(ttk.Frame):
    """
    A self-contained dashboard frame for the AegisGRID UI.
    This component encapsulates all the main real-time display widgets.
    """
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.configure(style="TFrame")

        self._create_widgets()

    def _create_widgets(self):
        """Creates and arranges all the widgets within this dashboard frame."""
        # --- Main Status Display ---
        status_frame = ttk.Frame(self, style="TFrame")
        status_frame.pack(fill="x", pady=10)
        
        self.status_label = ttk.Label(status_frame, text="STANDBY", style="Status.TLabel", foreground="#FFA500")
        self.status_label.pack()
        
        self.reason_label = ttk.Label(status_frame, text="Simulation not started.", style="TLabel")
        self.reason_label.pack(pady=5)

        # --- Confidence Score ---
        confidence_frame = ttk.Frame(self)
        confidence_frame.pack(pady=10)
        
        ttk.Label(confidence_frame, text="Threat Confidence:", style="TLabel").pack(side="left", padx=5)
        self.confidence_progress = ttk.Progressbar(confidence_frame, orient="horizontal", length=300, mode="determinate")
        self.confidence_progress.pack(side="left")
        self.confidence_label = ttk.Label(confidence_frame, text="0%", style="TLabel", width=5)
        self.confidence_label.pack(side="left", padx=5)

        # --- Individual Analyzers ---
        analyzer_frame = ttk.Frame(self)
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

    def update_display(self, data: dict):
        """
        Updates all dashboard widgets with new data from the backend.

        Args:
            data (dict): A dictionary containing the latest fused alert status.
        """
        # Update Main Status
        if data['aegis_alert']:
            self.status_label.config(text="AEGIS ALERT", foreground="#FF4B4B")
        else:
            self.status_label.config(text="SYSTEM NOMINAL", foreground="#76FF03")
        
        self.reason_label.config(text=data['reason'])
        
        # Update Confidence Progress Bar
        confidence_percent = data['combined_confidence'] * 100
        self.confidence_progress['value'] = confidence_percent
        self.confidence_label.config(text=f"{confidence_percent:.0f}%")
        
        # Update Individual Analyzers
        scada_color = "#FFD700" if data['scada_anomaly'] else "white"
        self.scada_status_label.config(text=f"Status: {'ANOMALY' if data['scada_anomaly'] else 'Normal'}", foreground=scada_color)
        
        pmu_color = "#FFD700" if data['pmu_anomaly'] else "white"
        self.pmu_status_label.config(text=f"Status: {'ANOMALY' if data['pmu_anomaly'] else 'Normal'}", foreground=pmu_color)

