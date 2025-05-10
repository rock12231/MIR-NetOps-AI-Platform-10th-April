from typing import List, Dict, Any

def detect_flapping_interfaces(logs: List[Dict[str, Any]], time_threshold_minutes: int, min_transitions: int) -> List[Dict[str, Any]]:
    flapping_interfaces: List[Dict[str, Any]] = []
    interface_transitions: Dict[tuple, List[Dict[str, Any]]] = {}

    for log in logs:
        if not isinstance(log, dict):
            continue
        interface = log.get('interface')
        event_type = log.get('event_type')
        timestamp = log.get('timestamp') # Assuming Unix timestamp (seconds)
        device = log.get('device', 'unknown_device')
        location = log.get('location', 'unknown_location')

        if not all([interface, event_type, timestamp]) or not isinstance(timestamp, (int, float)):
            continue

        # Consider only IF_UP and IF_DOWN events for flapping
        if 'IF_UP' in event_type or 'IF_DOWN' in event_type:
            key = (device, location, interface) # Unique key for an interface on a device at a location
            if key not in interface_transitions:
                interface_transitions[key] = []
            interface_transitions[key].append({
                'timestamp': timestamp,
                'state': 'UP' if 'IF_UP' in event_type else 'DOWN'
            })

    for key, transitions in interface_transitions.items():
        device, location, interface_name = key
        if len(transitions) < 2: # Need at least two transitions to flap
            continue

        transitions.sort(key=lambda x: x['timestamp'])

        rapid_transition_count = 0
        actual_total_transitions = 0 # Count actual state changes
        
        last_state = transitions[0]['state']
        last_time = transitions[0]['timestamp']
        
        # Calculate total duration for context, e.g., over which flapping occurred
        first_transition_time = transitions[0]['timestamp']
        last_transition_time = transitions[-1]['timestamp']
        total_observation_duration_minutes = (last_transition_time - first_transition_time) / 60


        for i in range(1, len(transitions)):
            current_time = transitions[i]['timestamp']
            current_state = transitions[i]['state']

            if current_state != last_state: # A true state transition
                actual_total_transitions += 1
                time_diff_minutes = (current_time - last_time) / 60
                if time_diff_minutes <= time_threshold_minutes:
                    rapid_transition_count += 1
            
            last_state = current_state
            last_time = current_time

        if rapid_transition_count >= min_transitions:
            flapping_interfaces.append({
                'device': device,
                'location': location,
                'interface': interface_name,
                'transitions_count': actual_total_transitions + 1, # Original way of counting, or len(transitions)
                'rapid_transitions_detected': rapid_transition_count,
                'observation_duration_minutes': round(total_observation_duration_minutes, 2),
                'details': transitions # Optionally include raw transitions
            })
            
    return flapping_interfaces


def analyze_interface_stability(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    stability_metrics: Dict[tuple, Dict[str, Any]] = {}
    
    # Determine overall time span of the logs for frequency calculation
    timestamps = [log.get('timestamp') for log in logs if isinstance(log, dict) and log.get('timestamp') and isinstance(log.get('timestamp'), (int, float))]
    time_span_hours = 1.0 # Default to 1 hour if no valid timestamps or single timestamp
    if len(timestamps) > 1:
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        time_span_seconds = max_ts - min_ts
        if time_span_seconds > 0:
            time_span_hours = max(time_span_seconds / 3600, 0.01) # Avoid division by zero, ensure at least a small fraction of an hour

    for log in logs:
        if not isinstance(log, dict):
            continue
        interface = log.get('interface')
        event_type = log.get('event_type')
        device = log.get('device', 'unknown_device')
        location = log.get('location', 'unknown_location')
        severity_str = log.get('severity') # Severity might be string "0", "1", etc.

        if not interface or not event_type: # Basic requirements for this analysis
            continue

        key = (device, location, interface)
        if key not in stability_metrics:
            stability_metrics[key] = {
                'device': device,
                'location': location,
                'interface': interface,
                'total_events': 0,
                'down_events': 0, # Specifically count "IF_DOWN" or similar
                'severity_scores': [], # Store numeric severities
                'event_frequency_per_hour': 0.0, # Calculated later
                'stability_score': 100.0 # Calculated later, 0-100, higher is more stable
            }

        metrics = stability_metrics[key]
        metrics['total_events'] += 1
        if 'IF_DOWN' in event_type: # Assuming 'IF_DOWN' indicates an interface down event
            metrics['down_events'] += 1
        
        if severity_str is not None:
            try:
                severity_int = int(severity_str)
                metrics['severity_scores'].append(severity_int)
            except ValueError:
                pass # Ignore non-integer severities for score calculation

    stability_list: List[Dict[str, Any]] = []
    for key, metrics in stability_metrics.items():
        total_events = metrics['total_events']
        down_events = metrics['down_events']
        severity_scores = metrics['severity_scores']

        metrics['event_frequency_per_hour'] = round(total_events / time_span_hours, 2)
        
        # Calculate stability score (example heuristic)
        # Start with 100 (perfectly stable)
        current_score = 100.0
        
        # Penalty for down events
        down_ratio = (down_events / total_events) if total_events > 0 else 0
        current_score -= down_ratio * 50 # Max 50 points penalty for down ratio
        
        # Penalty for average severity (lower severity numbers are worse, e.g., 0-6 scale)
        if severity_scores:
            avg_severity = sum(severity_scores) / len(severity_scores)
            # Assuming 0 is critical, 6 is info. Normalize to a 0-1 penalty factor (0 = best, 1 = worst)
            # If scale is 0-6, ( (6-avg_severity) / 6 ) is a penalty factor.
            # This example uses a simpler approach: max penalty 30 points based on avg_severity.
            # Lower numeric severity = higher penalty.
            # E.g. if avg_severity is 0 (critical), penalty is high. If 6 (info), penalty low.
            # Example: penalty = ( (max_severity_value - avg_severity) / max_severity_value ) * max_penalty_points
            # Assuming severity 0-6: max_severity_value = 6
            severity_penalty_factor = ( (6 - avg_severity) / 6 ) if avg_severity <=6 else 0 # Normalize
            current_score -= severity_penalty_factor * 20 # Max 20 points penalty from severity
            metrics['average_severity'] = round(avg_severity, 2)

        # Penalty for high event frequency
        # Example: if frequency > 10 events/hour, start penalizing. Max 20 points.
        if metrics['event_frequency_per_hour'] > 5: # Threshold
             # Penalize more for higher frequencies, up to a cap
            frequency_penalty = min((metrics['event_frequency_per_hour'] / 20), 1.0) * 20 # Max 20 points
            current_score -= frequency_penalty
            
        metrics['stability_score'] = max(0, round(current_score, 1)) # Ensure score is between 0 and 100
        
        # Remove raw severity_scores from final output if not needed by client
        # del metrics['severity_scores'] 
        
        stability_list.append(metrics)

    return sorted(stability_list, key=lambda x: x['stability_score']) # Sort by stability score, least stable first