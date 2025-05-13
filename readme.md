# Network Monitoring Dashboard

A comprehensive multi-page Streamlit application for monitoring network devices, with a special focus on interface monitoring and stability analysis. This dashboard provides visualization and analysis capabilities for network device logs stored in a Qdrant vector database.

## Features

### 📊 Main Dashboard
- **Real-time Network Health Monitoring**: Track key metrics including total events, active devices, interface down events, and flapping interfaces
- **Event Timeline Analysis**: Visualize network events over time to identify patterns and anomalies
- **Event Category Distribution**: Understand the distribution of different event categories across your network
- **Severity Distribution**: Analyze events by severity level to prioritize critical issues
- **Time-based Heatmaps**: Visualize network activity patterns by hour and day of week
- **Location-based Analysis**: Compare event frequencies across different network locations
- **Log Explorer**: Search and browse through recent network events with detailed information

### 🔌 Interface Monitoring
- **Interface Status Summary**: Track interfaces with the most status changes and identify problematic interfaces
- **Flapping Interface Detection**: Identify and troubleshoot interfaces that frequently transition between up and down states
- **Stability Scoring**: Calculate interface stability scores based on:
  - Down events ratio (40%): Ratio of down events to total events
  - Event frequency (40%): Number of events per hour (capped at 5 events/hour)
  - Configuration changes (20%): Number of configuration changes (capped at 5 changes)
  - Formula: `stability_score = 100 - (40 * down_ratio + 40 * min(1, event_frequency/5) + 20 * min(1, config_changes/5))`
  - Higher scores (0-100) indicate more stable interfaces
- **Event Timeline Analysis**: Time-based visualization of interface events
- **Detailed Interface Diagnostics**: In-depth analysis of individual interface history and state transitions

## Prerequisites

- Python 3.8+
- Docker (optional, for containerized deployment)
- Access to a Qdrant database with network logs

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/network-monitoring-dashboard.git
   cd network-monitoring-dashboard
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the environment variables template:
   ```bash
   cp .env.example .env
   ```

4. Configure your environment variables in `.env`:
   ```
   QDRANT_HOST=your_qdrant_host
   QDRANT_PORT=6333
   ```

## Running the Dashboard

### Option 1: Direct Python Execution
```bash
chmod +x start.sh
./start.sh
```

### Option 2: Using Docker
```bash
docker-compose up -d
```

The dashboard will be available at `http://localhost:8501` by default.

## Project Structure

```
network_monitoring/
├── src/                    # Source code directory
│   ├── pages/             # Streamlit pages
│   │   ├── Dashboard.py           # Main dashboard page
│   │   └── Interface_Monitoring.py # Interface monitoring page
│   ├── utils/             # Utility modules
│   │   ├── data_processing.py     # Data processing utilities
│   │   ├── qdrant_client.py       # Qdrant database client
│   │   └── visualization.py       # Visualization utilities
│   ├── main.py            # Main application entry point
│   └── __init__.py        # Package initialization
├── data/                   # Data directory
├── logs/                   # Application logs
├── docker-compose.yaml     # Docker Compose configuration
├── Dockerfile             # Docker build configuration
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── .env.example          # Environment variables template
├── start.sh              # Startup script
└── remote-sync.sh        # Remote synchronization script
```

## Data Structure

The dashboard works with network log data stored in Qdrant collections following this naming pattern:
```
router_{device}_{location}_{type}_vector
```

Each record should contain fields like:
- `timestamp`: Unix timestamp
- `device`: Device identifier
- `location`: Location code
- `category`: Event category
- `event_type`: Specific event type
- `severity`: Severity level (0-6)
- `interface`: Interface identifier (if applicable)
- `raw_log`: Original log entry

## Troubleshooting

- **No data displayed**: Verify your Qdrant connection and collection names
- **Slow performance**: Try reducing the time range or applying more specific filters
- **Missing interface data**: Ensure your log parser correctly extracts interface identifiers
- **Collection not found**: Check if the collections in your Qdrant database match the expected pattern

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.



## API OUT PUT
#### api/v1/generate_summary
   ```
   { 
      "collection_name": "router_agw66_ym_log_vector",
      "limit": 2,
      "start_time": 1737849600,
      "end_time": 1746921540,
      "include_latest": false
   }
   ```
```
{
  "status": "success",
  "collection_name": "router_agw66_ym_log_vector",
  "points_count": 8959,
  "sample_size": 10,
  "device": "agw66",
  "location": "ym",
  "input_tokens": 4849,
  "output_tokens": 746,
  "analysis": {
    "timestamp": 1737869602,
    "original_timestamp": "2025-01-26 05:33:22",
    "device": "agw66",
    "location": "ym",
    "category": "ETHPORT",
    "event_type": "ETHPORT_SPEED",
    "severity": 5,
    "log_level": "notice",
    "raw_log": "Jan 26 05:33:22 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 26 10:33:22.852 UTC: %ETHPORT-5-SPEED: Interface Ethernet12/34, operational speed changed to 10 Gbps",
    "ingestion_time": "2025-03-27T15:43:23.990767",
    "ip_addresses": [],
    "interface": "Ethernet12/34",
    "source_ip": "172.18.0.6",
    "time_period_requested": {
      "start": "2025-01-26 00:00:00",
      "end": "2025-05-10 23:59:00"
    }
  },
  "sampled_logs": [
    {
      "timestamp": 1738113830,
      "original_timestamp": "2025-01-29 01:23:50",
      "device": "agw66",
      "location": "ym",
      "category": "ETHPORT",
      "event_type": "ETHPORT_IF_DUPLEX",
      "severity": "5",
      "log_level": "notice",
      "raw_log": "Jan 29 01:23:50 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 29 06:23:50.967 UTC: %ETHPORT-5-IF_DUPLEX: Interface Ethernet4/4, operational duplex mode changed to Full",
      "ingestion_time": "2025-03-27T15:52:52.085670",
      "ip_addresses": [],
      "interface": "Ethernet4/4",
      "source_ip": "172.18.0.6",
      "received_at": "2025-03-27T15:52:52.085058",
      "_node_content": "{\"id_\": \"002b0141-c42e-5cf1-2eaa-fbd30638f9e3\", \"embedding\": null, \"metadata\": {\"timestamp\": 1738113830, \"original_timestamp\": \"2025-01-29 01:23:50\", \"device\": \"agw66\", \"location\": \"ym\", \"category\": \"ETHPORT\", \"event_type\": \"ETHPORT_IF_DUPLEX\", \"severity\": \"5\", \"log_level\": \"notice\", \"raw_log\": \"Jan 29 01:23:50 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 29 06:23:50.967 UTC: %ETHPORT-5-IF_DUPLEX: Interface Ethernet4/4, operational duplex mode changed to Full\", \"ingestion_time\": \"2025-03-27T15:52:52.085670\", \"ip_addresses\": [], \"interface\": \"Ethernet4/4\", \"source_ip\": \"172.18.0.6\", \"received_at\": \"2025-03-27T15:52:52.085058\"}, \"excluded_embed_metadata_keys\": [], \"excluded_llm_metadata_keys\": [], \"relationships\": {}, \"metadata_template\": \"{key}: {value}\", \"metadata_separator\": \"\\n\", \"text\": \"Interface Ethernet4/4, operational duplex mode changed to Full\", \"mimetype\": \"text/plain\", \"start_char_idx\": null, \"end_char_idx\": null, \"metadata_seperator\": \"\\n\", \"text_template\": \"{metadata_str}\\n\\n{content}\", \"class_name\": \"TextNode\"}",
      "_node_type": "TextNode",
      "document_id": "None",
      "doc_id": "None",
      "ref_doc_id": "None"
    },
    {
      "timestamp": 1738150477,
      "original_timestamp": "2025-01-29 11:34:37",
      "device": "agw66",
      "location": "ym",
      "category": "ETHPORT",
      "event_type": "ETHPORT_IF_UP",
      "severity": "5",
      "log_level": "notice",
      "raw_log": "Jan 29 11:34:37 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 29 16:34:37.152 UTC: %ETHPORT-5-IF_UP: Interface Ethernet3/29 is up in mode access",
      "ingestion_time": "2025-03-27T15:54:15.644157",
      "ip_addresses": [],
      "interface": "Ethernet3/29",
      "source_ip": "172.18.0.6",
      "received_at": "2025-03-27T15:54:15.643577",
      "_node_content": "{\"id_\": \"003074e9-8a82-bfda-3a96-78f499382b7e\", \"embedding\": null, \"metadata\": {\"timestamp\": 1738150477, \"original_timestamp\": \"2025-01-29 11:34:37\", \"device\": \"agw66\", \"location\": \"ym\", \"category\": \"ETHPORT\", \"event_type\": \"ETHPORT_IF_UP\", \"severity\": \"5\", \"log_level\": \"notice\", \"raw_log\": \"Jan 29 11:34:37 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 29 16:34:37.152 UTC: %ETHPORT-5-IF_UP: Interface Ethernet3/29 is up in mode access\", \"ingestion_time\": \"2025-03-27T15:54:15.644157\", \"ip_addresses\": [], \"interface\": \"Ethernet3/29\", \"source_ip\": \"172.18.0.6\", \"received_at\": \"2025-03-27T15:54:15.643577\"}, \"excluded_embed_metadata_keys\": [], \"excluded_llm_metadata_keys\": [], \"relationships\": {}, \"metadata_template\": \"{key}: {value}\", \"metadata_separator\": \"\\n\", \"text\": \"Interface Ethernet3/29 is up in mode access\", \"mimetype\": \"text/plain\", \"start_char_idx\": null, \"end_char_idx\": null, \"metadata_seperator\": \"\\n\", \"text_template\": \"{metadata_str}\\n\\n{content}\", \"class_name\": \"TextNode\"}",
      "_node_type": "TextNode",
      "document_id": "None",
      "doc_id": "None",
      "ref_doc_id": "None"
    },
    {
      "timestamp": 1738059237,
      "original_timestamp": "2025-01-28 10:13:57",
      "device": "agw66",
      "location": "ym",
      "category": "ETHPORT",
      "event_type": "ETHPORT_IF_DOWN_LINK_FAILURE",
      "severity": "5",
      "log_level": "notice",
      "raw_log": "Jan 28 10:13:57 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 28 15:13:57.637 UTC: %ETHPORT-5-IF_DOWN_LINK_FAILURE: Interface Ethernet5/3 is down (Link failure)",
      "ingestion_time": "2025-03-27T15:50:49.006239",
      "ip_addresses": [],
      "interface": "Ethernet5/3",
      "source_ip": "172.18.0.6",
      "received_at": "2025-03-27T15:50:49.005731",
      "_node_content": "{\"id_\": \"00313395-98d0-27a1-7c30-f9718b3146a1\", \"embedding\": null, \"metadata\": {\"timestamp\": 1738059237, \"original_timestamp\": \"2025-01-28 10:13:57\", \"device\": \"agw66\", \"location\": \"ym\", \"category\": \"ETHPORT\", \"event_type\": \"ETHPORT_IF_DOWN_LINK_FAILURE\", \"severity\": \"5\", \"log_level\": \"notice\", \"raw_log\": \"Jan 28 10:13:57 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 28 15:13:57.637 UTC: %ETHPORT-5-IF_DOWN_LINK_FAILURE: Interface Ethernet5/3 is down (Link failure)\", \"ingestion_time\": \"2025-03-27T15:50:49.006239\", \"ip_addresses\": [], \"interface\": \"Ethernet5/3\", \"source_ip\": \"172.18.0.6\", \"received_at\": \"2025-03-27T15:50:49.005731\"}, \"excluded_embed_metadata_keys\": [], \"excluded_llm_metadata_keys\": [], \"relationships\": {}, \"metadata_template\": \"{key}: {value}\", \"metadata_separator\": \"\\n\", \"text\": \"Interface Ethernet5/3 is down (Link failure)\", \"mimetype\": \"text/plain\", \"start_char_idx\": null, \"end_char_idx\": null, \"metadata_seperator\": \"\\n\", \"text_template\": \"{metadata_str}\\n\\n{content}\", \"class_name\": \"TextNode\"}",
      "_node_type": "TextNode",
      "document_id": "None",
      "doc_id": "None",
      "ref_doc_id": "None"
    },
    {
      "timestamp": 1737857786,
      "original_timestamp": "2025-01-26 02:16:26",
      "device": "agw66",
      "location": "ym",
      "category": "ETHPORT",
      "event_type": "ETHPORT_IF_TX_FLOW_CONTROL",
      "severity": "5",
      "log_level": "notice",
      "raw_log": "Jan 26 02:16:26 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 26 07:16:26.811 UTC: %ETHPORT-5-IF_TX_FLOW_CONTROL: Interface Ethernet3/29, operational Transmit Flow Control state changed to off",
      "ingestion_time": "2025-03-27T15:42:54.237950",
      "ip_addresses": [],
      "interface": "Ethernet3/29",
      "source_ip": "172.18.0.6",
      "received_at": "2025-03-27T15:42:52.881640",
      "_node_content": "{\"id_\": \"004052f1-1e11-6486-3697-d173526a2346\", \"embedding\": null, \"metadata\": {\"timestamp\": 1737857786, \"original_timestamp\": \"2025-01-26 02:16:26\", \"device\": \"agw66\", \"location\": \"ym\", \"category\": \"ETHPORT\", \"event_type\": \"ETHPORT_IF_TX_FLOW_CONTROL\", \"severity\": \"5\", \"log_level\": \"notice\", \"raw_log\": \"Jan 26 02:16:26 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 26 07:16:26.811 UTC: %ETHPORT-5-IF_TX_FLOW_CONTROL: Interface Ethernet3/29, operational Transmit Flow Control state changed to off\", \"ingestion_time\": \"2025-03-27T15:42:54.237950\", \"ip_addresses\": [], \"interface\": \"Ethernet3/29\", \"source_ip\": \"172.18.0.6\", \"received_at\": \"2025-03-27T15:42:52.881640\"}, \"excluded_embed_metadata_keys\": [], \"excluded_llm_metadata_keys\": [], \"relationships\": {}, \"metadata_template\": \"{key}: {value}\", \"metadata_separator\": \"\\n\", \"text\": \"Interface Ethernet3/29, operational Transmit Flow Control state changed to off\", \"mimetype\": \"text/plain\", \"start_char_idx\": null, \"end_char_idx\": null, \"metadata_seperator\": \"\\n\", \"text_template\": \"{metadata_str}\\n\\n{content}\", \"class_name\": \"TextNode\"}",
      "_node_type": "TextNode",
      "document_id": "None",
      "doc_id": "None",
      "ref_doc_id": "None"
    },
    {
      "timestamp": 1738120807,
      "original_timestamp": "2025-01-29 03:20:07",
      "device": "agw66",
      "location": "ym",
      "category": "ETHPORT",
      "event_type": "ETHPORT_SPEED",
      "severity": "5",
      "log_level": "notice",
      "raw_log": "Jan 29 03:20:07 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 29 08:20:07.964 UTC: %ETHPORT-5-SPEED: Interface Ethernet4/4, operational speed changed to 1 Gbps",
      "ingestion_time": "2025-03-27T15:53:08.723973",
      "ip_addresses": [],
      "interface": "Ethernet4/4",
      "source_ip": "172.18.0.6",
      "received_at": "2025-03-27T15:53:08.723377",
      "_node_content": "{\"id_\": \"00473a68-9f2e-4b64-e657-00e032db90f3\", \"embedding\": null, \"metadata\": {\"timestamp\": 1738120807, \"original_timestamp\": \"2025-01-29 03:20:07\", \"device\": \"agw66\", \"location\": \"ym\", \"category\": \"ETHPORT\", \"event_type\": \"ETHPORT_SPEED\", \"severity\": \"5\", \"log_level\": \"notice\", \"raw_log\": \"Jan 29 03:20:07 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 29 08:20:07.964 UTC: %ETHPORT-5-SPEED: Interface Ethernet4/4, operational speed changed to 1 Gbps\", \"ingestion_time\": \"2025-03-27T15:53:08.723973\", \"ip_addresses\": [], \"interface\": \"Ethernet4/4\", \"source_ip\": \"172.18.0.6\", \"received_at\": \"2025-03-27T15:53:08.723377\"}, \"excluded_embed_metadata_keys\": [], \"excluded_llm_metadata_keys\": [], \"relationships\": {}, \"metadata_template\": \"{key}: {value}\", \"metadata_separator\": \"\\n\", \"text\": \"Interface Ethernet4/4, operational speed changed to 1 Gbps\", \"mimetype\": \"text/plain\", \"start_char_idx\": null, \"end_char_idx\": null, \"metadata_seperator\": \"\\n\", \"text_template\": \"{metadata_str}\\n\\n{content}\", \"class_name\": \"TextNode\"}",
      "_node_type": "TextNode",
      "document_id": "None",
      "doc_id": "None",
      "ref_doc_id": "None"
    },
    {
      "timestamp": 1737852989,
      "original_timestamp": "2025-01-26 00:56:29",
      "device": "agw66",
      "location": "ym",
      "category": "ETHPORT",
      "event_type": "ETHPORT_SPEED",
      "severity": "5",
      "log_level": "notice",
      "raw_log": "Jan 26 00:56:29 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 26 05:56:29.839 UTC: %ETHPORT-5-SPEED: Interface Ethernet5/3, operational speed changed to 1 Gbps",
      "ingestion_time": "2025-03-27T15:42:45.409498",
      "ip_addresses": [],
      "interface": "Ethernet5/3",
      "source_ip": "172.18.0.6",
      "received_at": "2025-03-27T15:42:41.638904",
      "_node_content": "{\"id_\": \"0049dfc4-0e60-41c9-4da0-12f55747d5be\", \"embedding\": null, \"metadata\": {\"timestamp\": 1737852989, \"original_timestamp\": \"2025-01-26 00:56:29\", \"device\": \"agw66\", \"location\": \"ym\", \"category\": \"ETHPORT\", \"event_type\": \"ETHPORT_SPEED\", \"severity\": \"5\", \"log_level\": \"notice\", \"raw_log\": \"Jan 26 00:56:29 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 26 05:56:29.839 UTC: %ETHPORT-5-SPEED: Interface Ethernet5/3, operational speed changed to 1 Gbps\", \"ingestion_time\": \"2025-03-27T15:42:45.409498\", \"ip_addresses\": [], \"interface\": \"Ethernet5/3\", \"source_ip\": \"172.18.0.6\", \"received_at\": \"2025-03-27T15:42:41.638904\"}, \"excluded_embed_metadata_keys\": [], \"excluded_llm_metadata_keys\": [], \"relationships\": {}, \"metadata_template\": \"{key}: {value}\", \"metadata_separator\": \"\\n\", \"text\": \"Interface Ethernet5/3, operational speed changed to 1 Gbps\", \"mimetype\": \"text/plain\", \"start_char_idx\": null, \"end_char_idx\": null, \"metadata_seperator\": \"\\n\", \"text_template\": \"{metadata_str}\\n\\n{content}\", \"class_name\": \"TextNode\"}",
      "_node_type": "TextNode",
      "document_id": "None",
      "doc_id": "None",
      "ref_doc_id": "None"
    },
    {
      "timestamp": 1738123076,
      "original_timestamp": "2025-01-29 03:57:56",
      "device": "agw66",
      "location": "ym",
      "category": "ETHPORT",
      "event_type": "ETHPORT_IF_TX_FLOW_CONTROL",
      "severity": "5",
      "log_level": "notice",
      "raw_log": "Jan 29 03:57:56 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 29 08:57:55.996 UTC: %ETHPORT-5-IF_TX_FLOW_CONTROL: Interface Ethernet3/29, operational Transmit Flow Control state changed to off",
      "ingestion_time": "2025-03-27T15:53:15.771325",
      "ip_addresses": [],
      "interface": "Ethernet3/29",
      "source_ip": "172.18.0.6",
      "received_at": "2025-03-27T15:53:15.770839",
      "_node_content": "{\"id_\": \"004aca3b-c96b-7f58-89d0-44d57aade21e\", \"embedding\": null, \"metadata\": {\"timestamp\": 1738123076, \"original_timestamp\": \"2025-01-29 03:57:56\", \"device\": \"agw66\", \"location\": \"ym\", \"category\": \"ETHPORT\", \"event_type\": \"ETHPORT_IF_TX_FLOW_CONTROL\", \"severity\": \"5\", \"log_level\": \"notice\", \"raw_log\": \"Jan 29 03:57:56 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 29 08:57:55.996 UTC: %ETHPORT-5-IF_TX_FLOW_CONTROL: Interface Ethernet3/29, operational Transmit Flow Control state changed to off\", \"ingestion_time\": \"2025-03-27T15:53:15.771325\", \"ip_addresses\": [], \"interface\": \"Ethernet3/29\", \"source_ip\": \"172.18.0.6\", \"received_at\": \"2025-03-27T15:53:15.770839\"}, \"excluded_embed_metadata_keys\": [], \"excluded_llm_metadata_keys\": [], \"relationships\": {}, \"metadata_template\": \"{key}: {value}\", \"metadata_separator\": \"\\n\", \"text\": \"Interface Ethernet3/29, operational Transmit Flow Control state changed to off\", \"mimetype\": \"text/plain\", \"start_char_idx\": null, \"end_char_idx\": null, \"metadata_seperator\": \"\\n\", \"text_template\": \"{metadata_str}\\n\\n{content}\", \"class_name\": \"TextNode\"}",
      "_node_type": "TextNode",
      "document_id": "None",
      "doc_id": "None",
      "ref_doc_id": "None"
    },
    {
      "timestamp": 1737895461,
      "original_timestamp": "2025-01-26 12:44:21",
      "device": "agw66",
      "location": "ym",
      "category": "ETHPORT",
      "event_type": "ETHPORT_IF_TX_FLOW_CONTROL",
      "severity": "5",
      "log_level": "notice",
      "raw_log": "Jan 26 12:44:21 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 26 17:44:21.955 UTC: %ETHPORT-5-IF_TX_FLOW_CONTROL: Interface Ethernet4/3, operational Transmit Flow Control state changed to off",
      "ingestion_time": "2025-03-27T15:44:24.092672",
      "ip_addresses": [],
      "interface": "Ethernet4/3",
      "source_ip": "172.18.0.6",
      "received_at": "2025-03-27T15:44:23.926298",
      "_node_content": "{\"id_\": \"0055415c-27ac-4a68-4672-f1f25e1430c0\", \"embedding\": null, \"metadata\": {\"timestamp\": 1737895461, \"original_timestamp\": \"2025-01-26 12:44:21\", \"device\": \"agw66\", \"location\": \"ym\", \"category\": \"ETHPORT\", \"event_type\": \"ETHPORT_IF_TX_FLOW_CONTROL\", \"severity\": \"5\", \"log_level\": \"notice\", \"raw_log\": \"Jan 26 12:44:21 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 26 17:44:21.955 UTC: %ETHPORT-5-IF_TX_FLOW_CONTROL: Interface Ethernet4/3, operational Transmit Flow Control state changed to off\", \"ingestion_time\": \"2025-03-27T15:44:24.092672\", \"ip_addresses\": [], \"interface\": \"Ethernet4/3\", \"source_ip\": \"172.18.0.6\", \"received_at\": \"2025-03-27T15:44:23.926298\"}, \"excluded_embed_metadata_keys\": [], \"excluded_llm_metadata_keys\": [], \"relationships\": {}, \"metadata_template\": \"{key}: {value}\", \"metadata_separator\": \"\\n\", \"text\": \"Interface Ethernet4/3, operational Transmit Flow Control state changed to off\", \"mimetype\": \"text/plain\", \"start_char_idx\": null, \"end_char_idx\": null, \"metadata_seperator\": \"\\n\", \"text_template\": \"{metadata_str}\\n\\n{content}\", \"class_name\": \"TextNode\"}",
      "_node_type": "TextNode",
      "document_id": "None",
      "doc_id": "None",
      "ref_doc_id": "None"
    },
    {
      "timestamp": 1738078286,
      "original_timestamp": "2025-01-28 15:31:26",
      "device": "agw66",
      "location": "ym",
      "category": "ETHPORT",
      "event_type": "ETHPORT_IF_DOWN_LINK_FAILURE",
      "severity": "5",
      "log_level": "notice",
      "raw_log": "Jan 28 15:31:26 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 28 20:31:26.776 UTC: %ETHPORT-5-IF_DOWN_LINK_FAILURE: Interface Ethernet4/3 is down (Link failure)",
      "ingestion_time": "2025-03-27T15:51:33.419933",
      "ip_addresses": [],
      "interface": "Ethernet4/3",
      "source_ip": "172.18.0.6",
      "received_at": "2025-03-27T15:51:33.419238",
      "_node_content": "{\"id_\": \"0055fa5a-77c0-402d-c6da-1ddb65ace12c\", \"embedding\": null, \"metadata\": {\"timestamp\": 1738078286, \"original_timestamp\": \"2025-01-28 15:31:26\", \"device\": \"agw66\", \"location\": \"ym\", \"category\": \"ETHPORT\", \"event_type\": \"ETHPORT_IF_DOWN_LINK_FAILURE\", \"severity\": \"5\", \"log_level\": \"notice\", \"raw_log\": \"Jan 28 15:31:26 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 28 20:31:26.776 UTC: %ETHPORT-5-IF_DOWN_LINK_FAILURE: Interface Ethernet4/3 is down (Link failure)\", \"ingestion_time\": \"2025-03-27T15:51:33.419933\", \"ip_addresses\": [], \"interface\": \"Ethernet4/3\", \"source_ip\": \"172.18.0.6\", \"received_at\": \"2025-03-27T15:51:33.419238\"}, \"excluded_embed_metadata_keys\": [], \"excluded_llm_metadata_keys\": [], \"relationships\": {}, \"metadata_template\": \"{key}: {value}\", \"metadata_separator\": \"\\n\", \"text\": \"Interface Ethernet4/3 is down (Link failure)\", \"mimetype\": \"text/plain\", \"start_char_idx\": null, \"end_char_idx\": null, \"metadata_seperator\": \"\\n\", \"text_template\": \"{metadata_str}\\n\\n{content}\", \"class_name\": \"TextNode\"}",
      "_node_type": "TextNode",
      "document_id": "None",
      "doc_id": "None",
      "ref_doc_id": "None"
    },
    {
      "timestamp": 1737869602,
      "original_timestamp": "2025-01-26 05:33:22",
      "device": "agw66",
      "location": "ym",
      "category": "ETHPORT",
      "event_type": "ETHPORT_SPEED",
      "severity": "5",
      "log_level": "notice",
      "raw_log": "Jan 26 05:33:22 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 26 10:33:22.852 UTC: %ETHPORT-5-SPEED: Interface Ethernet12/34, operational speed changed to 10 Gbps",
      "ingestion_time": "2025-03-27T15:43:23.990767",
      "ip_addresses": [],
      "interface": "Ethernet12/34",
      "source_ip": "172.18.0.6",
      "received_at": "2025-03-27T15:43:22.973047",
      "_node_content": "{\"id_\": \"005cccb2-20bf-fb7c-ed68-c242fcba7ded\", \"embedding\": null, \"metadata\": {\"timestamp\": 1737869602, \"original_timestamp\": \"2025-01-26 05:33:22\", \"device\": \"agw66\", \"location\": \"ym\", \"category\": \"ETHPORT\", \"event_type\": \"ETHPORT_SPEED\", \"severity\": \"5\", \"log_level\": \"notice\", \"raw_log\": \"Jan 26 05:33:22 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 26 10:33:22.852 UTC: %ETHPORT-5-SPEED: Interface Ethernet12/34, operational speed changed to 10 Gbps\", \"ingestion_time\": \"2025-03-27T15:43:23.990767\", \"ip_addresses\": [], \"interface\": \"Ethernet12/34\", \"source_ip\": \"172.18.0.6\", \"received_at\": \"2025-03-27T15:43:22.973047\"}, \"excluded_embed_metadata_keys\": [], \"excluded_llm_metadata_keys\": [], \"relationships\": {}, \"metadata_template\": \"{key}: {value}\", \"metadata_separator\": \"\\n\", \"text\": \"Interface Ethernet12/34, operational speed changed to 10 Gbps\", \"mimetype\": \"text/plain\", \"start_char_idx\": null, \"end_char_idx\": null, \"metadata_seperator\": \"\\n\", \"text_template\": \"{metadata_str}\\n\\n{content}\", \"class_name\": \"TextNode\"}",
      "_node_type": "TextNode",
      "document_id": "None",
      "doc_id": "None",
      "ref_doc_id": "None"
    }
  ],
  "request_time_period": {
    "start": "2025-01-26 00:00:00",
    "end": "2025-05-10 23:59:00"
  }
}
```

##### api/v1/generate_summary

```
{
    "collection_name": "router_agw66_ym_log_vector",
    "limit": 2,
    "start_time": 1737849600,
    "end_time": 1746921540,
    "include_latest": true
}

```

```
{
  "status": "success",
  "collection_name": "router_agw66_ym_log_vector",
  "points_count": 8959,
  "sample_size": 2,
  "device": "agw66",
  "location": "ym",
  "input_tokens": 2125,
  "output_tokens": 115,
  "analysis": {
    "summary": "The logs primarily show routine interface status updates with no apparent security events or operational anomalies.",
    "normal_patterns": [
      "Routine ETHPORT interface status changes (e.g., duplex mode change, interface up)."
    ],
    "anomalies": [],
    "recommendations": [
      "No immediate actions required based on the provided logs."
    ],
    "devices_analyzed": [
      "agw66"
    ],
    "locations_analyzed": [
      "ym"
    ],
    "time_period": {
      "start": "2025-01-29T01:23:50Z",
      "end": "2025-01-29T11:34:37Z"
    },
    "time_period_requested": {
      "start": "2025-01-26 00:00:00",
      "end": "2025-05-10 23:59:00"
    }
  },
  "sampled_logs": [
    {
      "timestamp": 1738150477,
      "original_timestamp": "2025-01-29 11:34:37",
      "device": "agw66",
      "location": "ym",
      "category": "ETHPORT",
      "event_type": "ETHPORT_IF_UP",
      "severity": "5",
      "log_level": "notice",
      "raw_log": "Jan 29 11:34:37 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 29 16:34:37.152 UTC: %ETHPORT-5-IF_UP: Interface Ethernet3/29 is up in mode access",
      "ingestion_time": "2025-03-27T15:54:15.644157",
      "ip_addresses": [],
      "interface": "Ethernet3/29",
      "source_ip": "172.18.0.6",
      "received_at": "2025-03-27T15:54:15.643577",
      "_node_content": "{\"id_\": \"003074e9-8a82-bfda-3a96-78f499382b7e\", \"embedding\": null, \"metadata\": {\"timestamp\": 1738150477, \"original_timestamp\": \"2025-01-29 11:34:37\", \"device\": \"agw66\", \"location\": \"ym\", \"category\": \"ETHPORT\", \"event_type\": \"ETHPORT_IF_UP\", \"severity\": \"5\", \"log_level\": \"notice\", \"raw_log\": \"Jan 29 11:34:37 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 29 16:34:37.152 UTC: %ETHPORT-5-IF_UP: Interface Ethernet3/29 is up in mode access\", \"ingestion_time\": \"2025-03-27T15:54:15.644157\", \"ip_addresses\": [], \"interface\": \"Ethernet3/29\", \"source_ip\": \"172.18.0.6\", \"received_at\": \"2025-03-27T15:54:15.643577\"}, \"excluded_embed_metadata_keys\": [], \"excluded_llm_metadata_keys\": [], \"relationships\": {}, \"metadata_template\": \"{key}: {value}\", \"metadata_separator\": \"\\n\", \"text\": \"Interface Ethernet3/29 is up in mode access\", \"mimetype\": \"text/plain\", \"start_char_idx\": null, \"end_char_idx\": null, \"metadata_seperator\": \"\\n\", \"text_template\": \"{metadata_str}\\n\\n{content}\", \"class_name\": \"TextNode\"}",
      "_node_type": "TextNode",
      "document_id": "None",
      "doc_id": "None",
      "ref_doc_id": "None"
    },
    {
      "timestamp": 1738113830,
      "original_timestamp": "2025-01-29 01:23:50",
      "device": "agw66",
      "location": "ym",
      "category": "ETHPORT",
      "event_type": "ETHPORT_IF_DUPLEX",
      "severity": "5",
      "log_level": "notice",
      "raw_log": "Jan 29 01:23:50 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 29 06:23:50.967 UTC: %ETHPORT-5-IF_DUPLEX: Interface Ethernet4/4, operational duplex mode changed to Full",
      "ingestion_time": "2025-03-27T15:52:52.085670",
      "ip_addresses": [],
      "interface": "Ethernet4/4",
      "source_ip": "172.18.0.6",
      "received_at": "2025-03-27T15:52:52.085058",
      "_node_content": "{\"id_\": \"002b0141-c42e-5cf1-2eaa-fbd30638f9e3\", \"embedding\": null, \"metadata\": {\"timestamp\": 1738113830, \"original_timestamp\": \"2025-01-29 01:23:50\", \"device\": \"agw66\", \"location\": \"ym\", \"category\": \"ETHPORT\", \"event_type\": \"ETHPORT_IF_DUPLEX\", \"severity\": \"5\", \"log_level\": \"notice\", \"raw_log\": \"Jan 29 01:23:50 agw66.ym.mgmt.net.cable.rogers.com local3.notice: agw66.ym: 2025 Jan 29 06:23:50.967 UTC: %ETHPORT-5-IF_DUPLEX: Interface Ethernet4/4, operational duplex mode changed to Full\", \"ingestion_time\": \"2025-03-27T15:52:52.085670\", \"ip_addresses\": [], \"interface\": \"Ethernet4/4\", \"source_ip\": \"172.18.0.6\", \"received_at\": \"2025-03-27T15:52:52.085058\"}, \"excluded_embed_metadata_keys\": [], \"excluded_llm_metadata_keys\": [], \"relationships\": {}, \"metadata_template\": \"{key}: {value}\", \"metadata_separator\": \"\\n\", \"text\": \"Interface Ethernet4/4, operational duplex mode changed to Full\", \"mimetype\": \"text/plain\", \"start_char_idx\": null, \"end_char_idx\": null, \"metadata_seperator\": \"\\n\", \"text_template\": \"{metadata_str}\\n\\n{content}\", \"class_name\": \"TextNode\"}",
      "_node_type": "TextNode",
      "document_id": "None",
      "doc_id": "None",
      "ref_doc_id": "None"
    }
  ],
  "request_time_period": {
    "start": "2025-01-26 00:00:00",
    "end": "2025-05-10 23:59:00"
  }
}
```