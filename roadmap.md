# Network Monitoring Dashboard

A comprehensive multi-page Streamlit application for monitoring network devices, with a special focus on interface monitoring and stability analysis.

## Components

### 📊 Main Dashboard
The primary dashboard providing an overview of network health, events, and activity metrics, including:
- Real-time network health monitoring
- Event timeline and distribution analysis
- Severity distribution visualization
- Basic interface status information

### 🔌 Interface Monitoring Component
A specialized dashboard focused exclusively on network interface status, stability, and performance analysis:
- Flapping interface detection with configurable parameters
- Interface stability scoring using weighted metrics
- Event timeline visualization for pattern analysis
- Detailed interface diagnostics and event logs
- Interface activity heatmap by hour of day

### 📈 Network Analytics (Coming Soon)
Advanced analytics component for deeper insights including:
- Anomaly detection in network events
- Event correlation analysis
- Predictive insights and forecasting
- Temporal pattern analysis

## System Architecture

The application uses:
- **Streamlit** for the web interface
- **Qdrant** vector database for storing and querying network logs
- **Plotly** for interactive visualizations

## File Structure

```
network_monitoring/
├── app.py                 # Main application entry point
├── pages/
│   ├── 01_dashboard.py    # Main dashboard component
│   ├── 02_interface_monitoring.py  # Interface monitoring component
│   └── 03_analytics.py    # Placeholder for future analytics component
└── utils/
    ├── __init__.py
    ├── qdrant_client.py   # Shared Qdrant connection utilities
    ├── data_processing.py # Shared data processing functions
    └── visualization.py   # Shared visualization utilities
```

## Interface Monitoring Features

The Interface Monitoring Component provides:

### Interface Status Summary
Key metrics on interface activity including up/down events, configuration changes, and total monitored interfaces.

### Flapping Interface Detection
Advanced algorithms to detect and highlight interfaces that are frequently changing state within configurable time thresholds.

### Stability Scoring
Stability score calculations to identify the least stable interfaces in your network, based on:
- Down events ratio (40%)
- Event frequency (40%)
- Configuration changes (20%)

### Event Timeline Analysis
Time-based visualization of interface events to identify patterns and correlations.

### Detailed Interface Diagnostics
In-depth analysis of individual interface history, event logs, and state transitions.

## Usage

Run the application with:

```bash
streamlit run app.py
```

## Requirements

- Python 3.8+
- Streamlit
- Plotly
- Pandas
- Qdrant Client
- Loguru