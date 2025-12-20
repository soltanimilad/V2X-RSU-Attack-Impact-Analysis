V2X RSU Attack Impact Analysis
This repository contains the framework for simulating and analyzing a Lane Blocking Attack via a malicious Roadside Unit (RSU). By comparing a "Clean" (baseline) scenario with a "Blocked" (attack) scenario, researchers can quantify the impact of V2X-based misinformation on urban traffic flow.

🛠 Required Tools
To run this project, you must have the following versions installed:

SUMO: 1.22.0

OMNeT++: 6.1

Veins: 5.3.1

📂 Project Structure
veins_block: A modified Veins library containing the specific logic for the RSU speed-injection attack.

log_visualization.py: A Python-based analytics suite for generating comparative research charts.

🚀 Execution Guide
1. Workspace Preparation
Open OMNeT++ and create two separate workspaces to ensure clean data separation:

Blocked Workspace: Import the provided veins_block project.

Clean Workspace: Import the standard, unmodified veins (5.3.1) project.

2. File Deployment
Run your scenario generator application. Once the files are generated, copy them into the veins/examples/ folder of the respective workspace according to the format below:

A. Blocked Workspace (Attack Scenario)
Copy these files into the project directory:

.net.xml, .poly.xml, .rou.xml

_Blocked.omnetpp.ini

_Blocked.sumo.cfg

_Blocked.launchd.xml

B. Clean Workspace (Baseline Scenario)
Copy these files into the project directory:

.net.xml, .poly.xml, .rou.xml

_Clean.omnetpp.ini

_Clean.sumo.cfg

_Clean.launchd.xml

3. Running Simulations
Launch the simulation in the Clean workspace and wait for completion.

Launch the simulation in the Blocked workspace and wait for completion.

Ensure the output logs (TripInfo and Summary files) are saved in a folder named [ScenarioName]-logs.

📊 Data Visualization
After both simulations have finished, you can analyze the results using the built-in visualization tool:

Run the log_visualization program:

In the application GUI, enter the Scenario Name you created (e.g., VeinsScenario).

The program will automatically locate the Clean and Blocked files to generate comparative charts, including:

Network Congestion Spikes

Time Loss Distribution (Histogram)

Route Truncation Analysis

V2X Rerouting Efficiency
