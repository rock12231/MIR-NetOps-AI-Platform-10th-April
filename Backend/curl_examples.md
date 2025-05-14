# API Testing with Curl

This document provides examples of using curl to test the various API endpoints.

## System Endpoints

### Health Check
```bash
curl -X GET "http://localhost:8001/system/health"
```

### System Info
```bash
curl -X GET "http://localhost:8001/system/info"
```

## Network Overview API

### Get Network Metadata
```bash
curl -X GET "http://localhost:8001/api/v1/network/metadata"
```

### Get Collections
```bash
curl -X GET "http://localhost:8001/api/v1/network/collections"
```

### Get Aggregated Network Data
```bash
curl -X GET "http://localhost:8001/api/v1/network/aggregated_data?start_time=2025-01-26T00:00:00&end_time=2025-01-31T23:59:59&device_types=agw&device_types=fw"
```

### Get Aggregated Network Data with Location Filter
```bash
curl -X GET "http://localhost:8001/api/v1/network/aggregated_data?start_time=2025-01-26T00:00:00&end_time=2025-01-31T23:59:59&device_types=agw&device_types=fw&locations=ym&locations=dupt"
```

## Devices Dashboard API

### Get Collections for Devices
```bash
curl -X GET "http://localhost:8001/api/v1/devices/collections"
```

### Get Device Data
```bash
curl -X GET "http://localhost:8001/api/v1/devices/device_data?collection_name=router_agw66_ym_log_vector&start_time=2025-01-26T00:00:00&end_time=2025-01-31T23:59:59"
```

### Get Device Data with Filters
```bash
curl -X GET "http://localhost:8001/api/v1/devices/device_data?collection_name=router_agw66_ym_log_vector&start_time=2025-01-26T00:00:00&end_time=2025-01-31T23:59:59&category=ETHPORT&severity=3"
```

### Get Interface Data
```bash
curl -X GET "http://localhost:8001/api/v1/devices/interface_data?start_time=2025-01-26T00:00:00&end_time=2025-01-31T23:59:59&device_type=agw"
```

## Interface Monitoring API

### Get Interface Collections
```bash
curl -X GET "http://localhost:8001/api/v1/interfaces/collections?device_type=agw"
```

### Get Interface Data
```bash
curl -X GET "http://localhost:8001/api/v1/interfaces/interface_data?start_time=2025-01-26T00:00:00&end_time=2025-01-31T23:59:59"
```

### Get Interface Data with Filters
```bash
curl -X GET "http://localhost:8001/api/v1/interfaces/interface_data?start_time=2025-01-26T00:00:00&end_time=2025-01-31T23:59:59&device=agw66&location=ym&interface=Ethernet3/29"
```

### Detect Flapping Interfaces
```bash
curl -X GET "http://localhost:8001/api/v1/interfaces/detect_flapping?start_time=2025-01-26T00:00:00&end_time=2025-01-31T23:59:59&time_threshold_minutes=30&min_transitions=3"
```

### Analyze Interface Stability
```bash
curl -X GET "http://localhost:8001/api/v1/interfaces/analyze_stability?start_time=2025-01-26T00:00:00&end_time=2025-01-31T23:59:59&time_window_hours=24"
```

### Get Interface Metrics
```bash
curl -X GET "http://localhost:8001/api/v1/interfaces/interface_metrics?start_time=2025-01-26T00:00:00&end_time=2025-01-31T23:59:59&time_window_hours=24"
```

### Categorize Interface Events
```bash
curl -X GET "http://localhost:8001/api/v1/interfaces/categorize_events?start_time=2025-01-26T00:00:00&end_time=2025-01-31T23:59:59"
```

## AI Summary API

### Generate Summary
```bash
curl -X POST "http://localhost:8001/api/v1/generate_summary" \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [
      "Jan 26 00:01:23 router_agw66 Interface Ethernet3/29 changed state to down",
      "Jan 26 00:02:45 router_agw66 Interface Ethernet3/29 changed state to up",
      "Jan 26 00:10:12 router_agw66 System restarted"
    ],
    "max_tokens": 200
  }'
``` 