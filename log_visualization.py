import sys
import os
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QTabWidget, QPushButton, QLineEdit, 
    QTextEdit, QMessageBox, QHBoxLayout, QLabel, QFileDialog
)
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

# --- Data Containers ---
class TripData:
    def __init__(self, label: str):
        self.label = label
        self.depart = []
        self.duration = []
        self.time_loss = []
        self.waiting_time = []
        self.route_length = []
        self.count = 0
        self.reroutes = 0

class SummaryData:
    def __init__(self, label: str):
        self.label = label
        self.time = []
        self.running_vehicles = []
        self.mean_speed = []

# --- Matplotlib Integration ---
class PlotViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.canvas = None
        self.toolbar = None
        self.figure = None

    def set_plot(self, fig: Figure):
        if self.canvas:
            self.layout.removeWidget(self.toolbar)
            self.layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
            self.toolbar.deleteLater()
        self.figure = fig
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        self.canvas.draw()

# --- Worker Thread ---
class AnalysisWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, dict, str)

    def __init__(self, base_name: str, folder_path: str):
        super().__init__()
        self.base_name = base_name
        self.folder_path = folder_path

    def parse_trip(self, path, label) -> TripData:
        data = TripData(label)
        tree = ET.parse(path)
        root = tree.getroot()
        trips = root.findall('tripinfo')
        data.count = len(trips)
        for t in trips:
            data.depart.append(float(t.get('depart')))
            data.duration.append(float(t.get('duration')))
            data.time_loss.append(float(t.get('timeLoss')))
            data.waiting_time.append(float(t.get('waitingTime')))
            data.route_length.append(float(t.get('routeLength')))
            if int(t.get('rerouteNo', 0)) > 0:
                data.reroutes += 1
        return data

    def parse_sum(self, path, label) -> SummaryData:
        data = SummaryData(label)
        tree = ET.parse(path)
        for s in tree.getroot().findall('step'):
            data.time.append(float(s.get('time')))
            data.running_vehicles.append(int(s.get('running')))
            data.mean_speed.append(float(s.get('meanSpeed')))
        return data

    def run(self):
        try:
            b, f = self.base_name, self.folder_path
            paths = {
                'c_t': os.path.join(f, f"{b}_Clean_tripinfo_output.xml"),
                'b_t': os.path.join(f, f"{b}_Blocked_tripinfo_output.xml"),
                'c_s': os.path.join(f, f"{b}_Clean_summary_output.xml"),
                'b_s': os.path.join(f, f"{b}_Blocked_summary_output.xml")
            }

            self.log_signal.emit(f"📊 Analyzing files for scenario: {b}")
            ct, bt = self.parse_trip(paths['c_t'], "Clean"), self.parse_trip(paths['b_t'], "Blocked")
            cs, bs = self.parse_sum(paths['c_s'], "Clean"), self.parse_sum(paths['b_s'], "Blocked")

            figs = {}

            # 1. Congestion (Summary)
            f1 = Figure(); ax = f1.add_subplot(111)
            ax.plot(cs.time, cs.running_vehicles, label="Clean", color='blue')
            ax.plot(bs.time, bs.running_vehicles, label="Blocked", color='red')
            ax.set_title("Network Congestion (Active Vehicles)"); ax.set_xlabel("Time (s)"); ax.legend(); figs['congestion'] = f1

            # 2. Time Loss Distribution
            f2 = Figure(); ax = f2.add_subplot(111)
            ax.hist(ct.time_loss, bins=30, alpha=0.5, label='Clean', color='blue', density=True)
            ax.hist(bt.time_loss, bins=30, alpha=0.5, label='Blocked', color='red', density=True)
            ax.set_title("Time Loss Probability Density"); ax.set_xlabel("Seconds Lost"); ax.legend(); figs['distribution'] = f2

            # 3. Time Loss Scatter
            f3 = Figure(); ax = f3.add_subplot(111)
            ax.scatter(ct.depart, ct.time_loss, color='blue', s=5, alpha=0.2, label="Clean")
            ax.scatter(bt.depart, bt.time_loss, color='red', s=8, alpha=0.4, label="Blocked")
            ax.set_title("Impact Timing (Departure vs Delay)"); ax.set_xlabel("Departure Time (s)"); ax.set_ylabel("Time Loss (s)"); ax.legend(); figs['scatter'] = f3

            # 4. Route Truncation (Boxplot)
            f4 = Figure(); ax = f4.add_subplot(111)
            ax.boxplot([ct.route_length, bt.route_length], labels=['Clean', 'Blocked'])
            ax.set_title("Route Length Comparison"); ax.set_ylabel("Distance (m)"); figs['length'] = f4

            # 5. Delay Averages
            f5 = Figure(); ax = f5.add_subplot(111)
            metrics = ['Duration', 'TimeLoss', 'Waiting']
            c_vals = [np.mean(ct.duration), np.mean(ct.time_loss), np.mean(ct.waiting_time)]
            b_vals = [np.mean(bt.duration), np.mean(bt.time_loss), np.mean(bt.waiting_time)]
            x = np.arange(len(metrics))
            ax.bar(x - 0.2, c_vals, 0.4, label='Clean', color='skyblue')
            ax.bar(x + 0.2, b_vals, 0.4, label='Blocked', color='salmon')
            ax.set_xticks(x); ax.set_xticklabels(metrics); ax.set_title("Average Impact per Vehicle"); ax.legend(); figs['bars'] = f5

            # RESTORED DETAILED REPORT
            # Calculate Differences
            # Calculate Averages and Mean Speed
            clean_mean_speed = np.mean(cs.mean_speed)
            blocked_mean_speed = np.mean(bs.mean_speed)
            speed_reduction = clean_mean_speed - blocked_mean_speed
            speed_reduction_pct = (speed_reduction / clean_mean_speed) * 100 if clean_mean_speed > 0 else 0

            report = (f"RESEARCH SUMMARY: {b}\n" + "="*45 +
                     f"\n[VEHICLE STATS]"
                     f"\nTotal Vehicles (Clean):      {ct.count}"
                     f"\nTotal Vehicles (Blocked):    {bt.count}"
                     f"\nVehicles Rerouted (Clean):   {ct.reroutes} ({ct.reroutes/ct.count*100:.1f}%)"
                     f"\nVehicles Rerouted (Blocked): {bt.reroutes} ({bt.reroutes/bt.count*100:.1f}%)"
                     
                     f"\n\n[SPEED & THROUGHPUT]"
                     f"\nAvg Mean Speed (Clean):      {clean_mean_speed:.2f} m/s"
                     f"\nAvg Mean Speed (Blocked):    {blocked_mean_speed:.2f} m/s"
                     f"\nSPEED REDUCTION:             -{speed_reduction:.2f} m/s ({speed_reduction_pct:.1f}%)"
                     
                     f"\n\n[TIME LOSS ANALYSIS]"
                     f"\nAvg Time Loss (Clean):       {np.mean(ct.time_loss):.1f}s"
                     f"\nAvg Time Loss (Blocked):     {np.mean(bt.time_loss):.1f}s"
                     f"\nATTACK IMPACT (Added Delay): +{np.mean(bt.time_loss) - np.mean(ct.time_loss):.2f}s"
                     
                     f"\n\n[EXTREME VALUES & VARIANCE]"
                     f"\nMax Time Loss (Clean):       {np.max(ct.time_loss):.1f}s"
                     f"\nMax Time Loss (Blocked):     {np.max(bt.time_loss):.1f}s"
                     f"\nStd Dev Time Loss (Clean):   {np.std(ct.time_loss):.2f}"
                     f"\nStd Dev Time Loss (Blocked): {np.std(bt.time_loss):.2f}"
                     
                     f"\n\n[WAITING TIME]"
                     f"\nAvg Waiting (Clean):         {np.mean(ct.waiting_time):.1f}s"
                     f"\nAvg Waiting (Blocked):       {np.mean(bt.waiting_time):.1f}s"
                     
                     f"\n\n[ROUTE ANALYSIS]"
                     f"\nAvg Route Length (Clean):    {np.mean(ct.route_length):.1f}m"
                     f"\nAvg Route Length (Blocked):  {np.mean(bt.route_length):.1f}m")

            self.finished_signal.emit(True, figs, report)
        except Exception as e:
            self.log_signal.emit(f"❌ Error: {str(e)}"); self.finished_signal.emit(False, {}, "")

# --- Main UI ---
class AdvancedVisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("V2X Attack - Research Analytics Suite")
        self.resize(1200, 900)
        self.figs = {}
        
        container = QWidget(); self.setCentralWidget(container)
        main_layout = QVBoxLayout(container)

        controls = QHBoxLayout()
        self.base_in = QLineEdit("VeinsScenario")
        self.path_in = QLineEdit(os.getcwd())
        
        self.btn_browse = QPushButton("Select Parent Folder")
        self.btn = QPushButton("Run Analysis")
        self.btn_save = QPushButton("Export All PNGs")
        self.btn_save.setEnabled(False)
        
        self.btn_browse.clicked.connect(self.browse_folder)
        self.btn.clicked.connect(self.run_analysis)
        self.btn_save.clicked.connect(self.save_all)
        
        controls.addWidget(QLabel("Scenario Name:")); controls.addWidget(self.base_in)
        controls.addWidget(self.btn_browse)
        controls.addWidget(QLabel("Search Path:")); controls.addWidget(self.path_in)
        controls.addWidget(self.btn); controls.addWidget(self.btn_save)
        main_layout.addLayout(controls)

        self.tabs = QTabWidget()
        self.log_view = QTextEdit()
        self.tab_congest = PlotViewer(); self.tab_dist = PlotViewer()
        self.tab_scatter = PlotViewer(); self.tab_length = PlotViewer()
        self.tab_bars = PlotViewer(); self.report_view = QTextEdit()
        self.report_view.setFontPointSize(11)

        self.tabs.addTab(self.log_view, "Status Log")
        self.tabs.addTab(self.tab_congest, "1. Congestion")
        self.tabs.addTab(self.tab_dist, "2. Time Loss Dist")
        self.tabs.addTab(self.tab_scatter, "3. Attack Timing")
        self.tabs.addTab(self.tab_length, "4. Route Lengths")
        self.tabs.addTab(self.tab_bars, "5. Averages")
        self.tabs.addTab(self.report_view, "6. Final Report")
        main_layout.addWidget(self.tabs)

    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Parent Directory")
        if path: self.path_in.setText(path)

    def run_analysis(self):
        self.log_view.clear()
        scenario = self.base_in.text()
        parent = self.path_in.text()
        target_logs = os.path.join(parent, f"{scenario}-logs")
        
        if not os.path.exists(target_logs):
            QMessageBox.warning(self, "Path Error", f"Folder not found:\n{target_logs}")
            return

        self.worker = AnalysisWorker(scenario, target_logs)
        self.worker.log_signal.connect(self.log_view.append)
        self.worker.finished_signal.connect(self.update_ui)
        self.worker.start()

    def update_ui(self, success, figs, report):
        if success:
            self.figs = figs
            self.tab_congest.set_plot(figs['congestion'])
            self.tab_dist.set_plot(figs['distribution'])
            self.tab_scatter.set_plot(figs['scatter'])
            self.tab_length.set_plot(figs['length'])
            self.tab_bars.set_plot(figs['bars'])
            self.report_view.setText(report)
            self.btn_save.setEnabled(True)
            self.tabs.setCurrentIndex(6)

    def save_all(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Folder to Save Charts")
        if dir_path:
            for name, fig in self.figs.items():
                fig.savefig(os.path.join(dir_path, f"Research_{name}.png"), dpi=300)
            QMessageBox.information(self, "Saved", "All charts exported.")

if __name__ == "__main__":
    app = QApplication(sys.argv); win = AdvancedVisApp(); win.show(); sys.exit(app.exec_())