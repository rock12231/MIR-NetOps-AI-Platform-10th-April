# --- START OF FILE 4_Chatbot.py ---

import streamlit as st
import os
import json
from typing import List, Tuple
# import logging # loguru is used, standard logging can be removed if not used elsewhere
from dotenv import load_dotenv
from loguru import logger
# Import necessary functions from auth module
from src.utils.auth import init_session_state, check_auth, logout
from datetime import datetime

# Load environment variables
load_dotenv()
# Path to metadata
METADATA_PATH = os.getenv("METADATA_PATH", "/app/data/qdrant_db_metadata.json")

# --- Page Configuration --- MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="AI Chatbot", # Simplified title
    page_icon="🤖",
    layout="wide"
)

# --- Initialize Session State and Authentication Check ---
# These should run right after page config and before any other Streamlit elements
init_session_state()
check_auth() # Check if user is logged in (using the backend token now), stops execution if not

# Log page access after successful auth check
# Use get method for safety in case username isn't set for some reason
logger.info(f"User '{st.session_state.get('username', 'Unknown')}' accessed Chatbot page.")

# Function to parse collections from metadata file
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_collections_from_json() -> List[Tuple[str, str, str]]:
    """Parses device, location, and type from collection names in the metadata file."""
    try:
        # Check if metadata file exists
        if not os.path.exists(METADATA_PATH):
            logger.error(f"Metadata file not found at: {METADATA_PATH}")
            st.error(f"Metadata file not found at the configured path ({METADATA_PATH}). Chatbot filters might be incomplete.")
            return []

        with open(METADATA_PATH, 'r') as f:
            metadata = json.load(f)

        if not isinstance(metadata, dict):
             logger.error("Metadata file content is not a dictionary.")
             st.error("Invalid metadata file format.")
             return []

        collections = metadata.get("collections", [])
        if not isinstance(collections, list):
             logger.error("Metadata 'collections' key is not a list.")
             st.error("Invalid metadata format: 'collections' should be a list.")
             return []

        parsed = []
        for name in collections:
            if not isinstance(name, str) or not (name.startswith("router_") and name.endswith("_vector")):
                logger.warning(f"Skipping invalid or non-router collection name: {name}")
                continue

            # Remove prefix and suffix
            core = name[len("router_"):-len("_vector")]
            parts = core.split("_")

            if len(parts) < 3:
                logger.warning(f"Skipping malformed collection name (too few parts): {name}")
                continue

            # Last part should be "log" or "config"
            data_type = parts[-1]
            if data_type not in ["log", "config"]:
                logger.warning(f"Skipping collection with invalid data_type '{data_type}': {name}")
                continue

            # Handle device/location parsing, including special cases like "new_fw"
            if parts[0] == "new" and len(parts) > 3: # e.g., new_fw66_qcmtl_log
                device = f"{parts[0]}_{parts[1]}" # device = "new_fw66"
                location = "_".join(parts[2:-1]) # location = "qcmtl"
            else: # e.g., agw1_locationA_log
                device = parts[0] # device = "agw1"
                location = "_".join(parts[1:-1]) # location = "locationA"

            if device and location:
                parsed.append((device, location, data_type))
            else:
                logger.warning(f"Could not parse valid device/location from: {name}")

        logger.info(f"Successfully parsed {len(parsed)} collections from {METADATA_PATH}")
        logger.debug(f"Parsed Collections: {parsed}")
        return parsed

    except FileNotFoundError:
        logger.error(f"Metadata file not found at: {METADATA_PATH}")
        st.error(f"Configuration Error: Metadata file not found at '{METADATA_PATH}'. Cannot load filters.")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse metadata JSON from {METADATA_PATH}: {e}", exc_info=True)
        st.error(f"Configuration Error: Error reading metadata file (invalid JSON).")
        return []
    except Exception as e:
        logger.error(f"Failed to load collections from {METADATA_PATH}: {e}", exc_info=True)
        st.error(f"An unexpected error occurred while loading metadata.")
        return []

@st.cache_data(ttl=3600, show_spinner="Loading network metadata...")  # Cache for 1 hour
def extract_network_metadata():
    """Extract valid device/location combinations and lists from parsed collections data."""
    try:
        collections_data = get_collections_from_json()

        location_devices = {}
        device_locations = {}

        for device, location, _ in collections_data:
            # Add device to location's set
            location_devices.setdefault(location, set()).add(device)
            # Add location to device's set
            device_locations.setdefault(device, set()).add(location)

        # Convert sets to sorted lists for consistent display
        locations = sorted(location_devices.keys())
        devices = sorted(device_locations.keys())

        # Prepare final structure with sorted lists
        processed_metadata = {
            "locations": locations,
            "devices": devices,
            "location_devices": {loc: sorted(list(devs)) for loc, devs in location_devices.items()},
            "device_locations": {dev: sorted(list(locs)) for dev, locs in device_locations.items()},
            "collections_data": collections_data # Keep the raw parsed data if needed elsewhere
        }
        logger.info("Network metadata extracted successfully.")
        return processed_metadata

    except Exception as e:
        logger.error(f"Error extracting network metadata: {e}", exc_info=True)
        st.error("Failed to process network metadata for filters.")
        # Return default structure on error
        return {
            "locations": [],
            "devices": [],
            "location_devices": {},
            "device_locations": {},
            "collections_data": []
        }

def chat_interface():
    """Handles the main chat interaction UI and logic."""
    # Initialize chat history in session state if it doesn't exist
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
        logger.info("Chat history initialized for session.")

    # Display a welcome message only once per session
    if "welcome_shown" not in st.session_state:
        st.markdown("""
        ### 🌟 Welcome to NetOps AI Chatbot! 🤖

        Hi! I'm here to assist with your network queries using recent syslog data. Ask me about:

        - 🖥️ **Network Health & Performance**: Status, metrics, and optimization.
        - ⚙️ **Devices & Ports**: Configurations, status, and changes.
        - 🛠️ **Troubleshooting & Events**: Issues, alerts, and system events.
        - 🌐 **And More!**: Any network-related question!

        #### 🔍 Filter Your Results:
        Use the sidebar filters (**👈**) to select specific devices and locations for more targeted queries!

        #### 💡 Try Asking:
        - "Summarize critical events for agw66 at ym in the last 24 hours."
        - "Which interfaces changed speed to 1Gbps recently?"
        - "Were there any BGP issues reported today?"

        Type your question below and I'll try to help! 🚀
        """)
        st.session_state["welcome_shown"] = True

    # Display past chat messages from history
    for i, msg in enumerate(st.session_state["messages"]):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Display sources section only for assistant messages that have sources
            if msg["role"] == "assistant" and "sources" in msg and msg["sources"]:
                with st.expander("View Sources", expanded=False): # Default to collapsed
                    # Create a container for the sources content
                    source_container = st.container()
                    with source_container:
                        raw_logs = []
                        valid_sources_found = False
                        for j, source in enumerate(msg["sources"]):
                            if not isinstance(source, dict): # Skip invalid source entries
                                logger.warning(f"Skipping invalid source entry at index {j}: {source}")
                                continue

                            metadata = source.get("metadata", {}) # Default to empty dict
                            if not isinstance(metadata, dict): # Ensure metadata is a dict
                                 logger.warning(f"Source {j} has invalid metadata format: {metadata}")
                                 metadata = {} # Reset to empty

                            raw_log = metadata.get("raw_log", "N/A")
                            # Ensure raw_log is a string
                            if not isinstance(raw_log, str):
                                raw_log = str(raw_log)

                            score = source.get("score") # Get score, could be None
                            score_str = f"{score:.4f}" if isinstance(score, (float, int)) else "N/A"

                            # Format the source display
                            numbered_log = f"**Source {j+1} (Score: {score_str})**\n```\n{raw_log}\n```"
                            raw_logs.append(numbered_log)
                            valid_sources_found = True

                        # Display collected raw logs
                        if valid_sources_found:
                            st.markdown("\n".join(raw_logs), unsafe_allow_html=False) # Use markdown, ensure HTML is not allowed
                        else:
                            st.info("No valid log sources found in the response.")

    # Accept user input via chat input widget
    user_input = st.chat_input("Ask about your network...")

    if user_input:
        # Get selected filters from session state (set by sidebar)
        selected_device = st.session_state.get("selected_device", "All Devices")
        selected_location = st.session_state.get("selected_location", "All Locations")

        # Construct context string for display purposes
        context_parts = []
        if selected_device != "All Devices":
            context_parts.append(f"Device='{selected_device}'") 
        if selected_location != "All Locations":
            context_parts.append(f"Location='{selected_location}'")

        # Add the user's original message to chat history
        st.session_state["messages"].append({"role": "user", "content": user_input})

        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(user_input)

        # --- Generate Mock Response (since backend API is not available) ---
        with st.spinner("🧠 NetOps AI is processing your request..."):
            try:
                # Add context info to the user message for display
                context_info = f" (Context: {' '.join(context_parts)})" if context_parts else ""
                
                # Generate mock response based on query
                mock_response = generate_mock_response(user_input, selected_device, selected_location)
                
                # Create mock sources
                mock_sources = [
                    {
                        "score": 0.95,
                        "metadata": {
                            "raw_log": f"Example log entry for {selected_device if selected_device != 'All Devices' else 'AGW1'} at {selected_location if selected_location != 'All Locations' else 'YM'}: Interface GigabitEthernet1/0/1 changed state to up",
                            "timestamp": 1649956800,  # Example timestamp (April 2022)
                            "event_type": "IF_UP",
                            "category": "ETHPORT",
                            "collection_name": "router_agw1_ym_log_vector"
                        }
                    },
                    {
                        "score": 0.87,
                        "metadata": {
                            "raw_log": f"Configuration change detected on {selected_device if selected_device != 'All Devices' else 'AGW66'}: interface speed set to 1Gbps",
                            "timestamp": 1649957400,  # 10 minutes later
                            "event_type": "CONFIG_CHANGE",
                            "category": "CONFIG",
                            "collection_name": "router_agw66_ym_log_vector"
                        }
                    }
                ]

                # Add assistant's response to chat history
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": mock_response,
                    "sources": mock_sources  # Include mock sources
                })
                logger.info("Generated mock chat response.")

            except Exception as e:
                error_msg = f"An unexpected error occurred: {str(e)}"
                logger.exception("Unexpected error during chat response generation:")
                st.error(error_msg)
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": f"⚠️ {error_msg}"
                })

        # Rerun the script to display the new message (user + assistant response/error)
        st.rerun()

def generate_mock_response(query, device, location):
    """
    Generate a mock response based on the query and selected filters.
    
    Args:
        query: The user's query
        device: The selected device filter
        location: The selected location filter
        
    Returns:
        str: A mock response
    """
    # Convert query to lowercase for easier matching
    query_lower = query.lower()
    
    # Build context info for the response
    context_info = ""
    if device != "All Devices":
        context_info += f" for device {device}"
    if location != "All Locations":
        context_info += f" at location {location}"
    
    # Default response if no patterns match
    default_response = f"Based on the logs{context_info}, I don't have specific information about that query. Could you try rephrasing or asking about interface status, configuration changes, or system events?"
    
    # Check for different query patterns and provide appropriate responses
    if any(word in query_lower for word in ["hello", "hi", "hey", "greetings"]):
        return f"Hello! How can I help you with your network monitoring{context_info} today?"
        
    elif "status" in query_lower or "health" in query_lower:
        return f"The network status{context_info} shows all systems operational. There have been no critical alerts in the past 24 hours."
        
    elif "interface" in query_lower and ("down" in query_lower or "up" in query_lower):
        if device != "All Devices":
            return f"For {device} at {location if location != 'All Locations' else 'all locations'}, 3 interfaces are currently down: GigabitEthernet1/0/8, GigabitEthernet2/0/11, and TenGigabitEthernet3/0/2. All other interfaces are up and operational."
        else:
            return "Across all monitored devices, 7 interfaces are currently down. The most recent down event was on AGW66 at YM for interface GigabitEthernet1/0/8 approximately 3 hours ago."
            
    elif "flapping" in query_lower:
        if device != "All Devices":
            return f"I've detected 2 flapping interfaces on {device}{context_info}: GigabitEthernet1/0/3 and GigabitEthernet1/0/7. The flapping started approximately 4 hours ago and is continuing intermittently."
        else:
            return "Across the network, 5 interfaces have been flapping in the last 24 hours. The most affected device is AGW1 with 3 flapping interfaces."
            
    elif "configuration" in query_lower or "config" in query_lower:
        return f"There have been 7 configuration changes{context_info} in the last 24 hours. The most recent was a speed change to 1Gbps on interface GigabitEthernet1/0/12."
        
    elif "bgp" in query_lower:
        if device != "All Devices":
            return f"BGP sessions for {device}{context_info} are stable. No BGP neighbor changes or routing updates have been detected in the past 24 hours."
        else:
            return "There was one BGP peer flap detected on AGW66 at YM approximately 6 hours ago, but it has since stabilized. All other BGP sessions are stable."
            
    elif "error" in query_lower or "critical" in query_lower or "alert" in query_lower:
        return f"I found 3 critical alerts{context_info} in the past 24 hours:\n1. High CPU utilization (95%) on AGW1 at 15:30 UTC\n2. Memory allocation failure on BGP process at 18:45 UTC\n3. Interface GigabitEthernet1/0/8 excessive errors at 22:10 UTC"
    
    # Return default response if no patterns match
    return default_response

# --- Sidebar Setup ---
with st.sidebar:
    st.subheader("Chat Options & Context")
    st.markdown("Filter the context provided to the AI for more targeted answers.")

    # Load metadata for filters
    network_meta = extract_network_metadata() # Renamed for clarity

    # Location Filter
    location_options = ["All Locations"] + network_meta.get("locations", [])
    selected_location = st.selectbox(
        "Filter by Location",
        options=location_options,
        index=0, # Default to "All Locations"
        key="selected_location", # Key used to store selection in session state
        help="Limit the AI's focus to a specific location."
    )

    # Device Filter (dynamically updated based on location)
    device_options = ["All Devices"] # Start with default
    if selected_location != "All Locations":
        # Get devices valid for the selected location
        valid_devices = network_meta.get("location_devices", {}).get(selected_location, [])
        device_options.extend(valid_devices)
        # Reset device selection if the current one becomes invalid
        current_device_selection = st.session_state.get("selected_device", "All Devices")
        if current_device_selection not in device_options:
            st.session_state.selected_device = "All Devices"
            logger.debug(f"Resetting device filter as '{current_device_selection}' is not valid for location '{selected_location}'.")
    else:
        # Show all devices if "All Locations" is selected
        device_options.extend(network_meta.get("devices", []))

    selected_device = st.selectbox(
        "Filter by Device",
        options=device_options,
        # Try to preserve selection if it's still valid in the options list
        index=device_options.index(st.session_state.get("selected_device", "All Devices")) if st.session_state.get("selected_device") in device_options else 0,
        key="selected_device", # Key used to store selection in session state
        help="Limit the AI's focus to a specific device."
    )

    st.markdown("---")

    # Chat Actions
    if st.button("Clear Chat History", key="clear_chat"):
        st.session_state["messages"] = []
        st.session_state.pop("welcome_shown", None) # Remove flag to show welcome message again
        logger.info("Chat history cleared by user.")
        st.rerun() # Rerun to reflect the cleared history

    # --- System Status / Health Check ---
    st.markdown("---")
    st.subheader("System Status")
    
    # Display mock system status instead of checking API health
    if st.button("Check System Status", key="check_system_status"):
        st.success("Mock Network Monitoring System is online ✅")
        st.info("Using local simulation mode - no backend API connection required")
        st.json({
            "status": "healthy",
            "mode": "simulation",
            "timestamp": datetime.now().isoformat(),
            "service": "mock_network_monitor"
        })
    
    # --- User/Logout Section ---
    st.markdown("---")
    st.subheader("User")
    # Safely display username
    username = st.session_state.get('username', 'N/A')
    st.write(f"👤 Logged in as: **{username}**")
    if st.button("Logout", key="logout_chat"):
        logout() # Call logout function from auth module

    st.markdown("---")
    st.caption("NetOps AI Chatbot v1.2")

# --- Main Page Content ---
st.title("🤖 AI Chatbot Interface")
st.markdown("Interact with the NetOps AI to analyze network logs and events.")

# Display the chat interface elements
chat_interface()

# --- JavaScript for Auto-Scrolling --- (Keep the improved version from previous step)
st.markdown("""
<script>
    function scrollToBottom() {
        const chatMessagesContainer = document.querySelector('[data-testid="stChatMessage"]')?.parentElement;
        if (chatMessagesContainer) {
            const lastMessage = chatMessagesContainer.lastElementChild;
            if (lastMessage) {
                lastMessage.scrollIntoView({ behavior: 'smooth', block: 'end' });
            } else {
                chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
            }
        }
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    const debouncedScrollToBottom = debounce(scrollToBottom, 150); // Slightly longer debounce

    const observer = new MutationObserver((mutationsList, observer) => {
        for(const mutation of mutationsList) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                const addedChatMessage = Array.from(mutation.addedNodes).some(node =>
                    node.nodeType === 1 && node.matches('[data-testid="stChatMessage"]')
                );
                if (addedChatMessage) {
                    debouncedScrollToBottom();
                    break;
                }
            }
        }
    });

    setTimeout(() => {
        // Try a more specific selector if possible, otherwise fallback
        const targetNode = window.parent.document.querySelector('.main .block-container') || window.parent.document.querySelector('.main > div') || document.body;

        if (targetNode) {
            console.log("Chat Scroll: Observer attached to:", targetNode);
            observer.observe(targetNode, { childList: true, subtree: true });
            setTimeout(scrollToBottom, 300); // Initial scroll attempt
        } else {
             console.warn("Chat Scroll: Could not find target node for MutationObserver.");
        }
    }, 700); // Increased delay to ensure elements are loaded

     window.addEventListener('beforeunload', () => {
         observer.disconnect();
         console.log("Chat Scroll: Observer disconnected.");
     });
</script>
""", unsafe_allow_html=True)
# --- END OF FILE 4_Chatbot.py ---