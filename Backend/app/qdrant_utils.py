import logging
from app.config import qdrant # Import the initialized Qdrant client

logger = logging.getLogger(__name__)

AVAILABLE_COLLECTIONS = [
    "router_agw66_ym_log_vector", "router_dgw70_baal_re0_log_vector", "router_dgw70_hnsn_re0_log_vector",
    "router_dgw70_pr_re0_log_vector", "router_dgw70_slnt_re0_log_vector", "router_dgw71_flfrd_re0_log_vector",
    "router_dgw71_grnsbr_re0_log_vector", "router_dgw71_pr_re0_log_vector", "router_dgw71_rchrd_re0_log_vector",
    "router_fw66_dupt_log_vector", "router_fw66_ed2_log_vector", "router_fw66_ms1_log_vector",
    "router_fw66_nbmn_log_vector", "router_fw66_to3_log_vector", "router_fw66_va2_log_vector",
    "router_fw66_wlfdle_log_vector", "router_fw66_ym_log_vector", "router_fw67_dupt_log_vector",
    "router_fw67_ed2_log_vector", "router_fw67_ms1_log_vector", "router_fw67_nbmn_log_vector",
    "router_fw67_to3_log_vector", "router_fw67_va2_log_vector", "router_fw67_wlfdle_log_vector",
    "router_new_fw66_qcmtl_log_vector", "router_new_fw67_qcmtl_log_vector", "router_vadc66a_ml02_log_vector"
]

DEFAULT_COLLECTION = "router_agw66_ym_log_vector"
VECTOR_SIZE = 384 # This seems to be an implicit constant from original code, might be model specific

def parse_collection_name_backend(name):
    prefix = "router_"
    suffix = "_log_vector"
    if name.startswith(prefix) and name.endswith(suffix):
        core = name[len(prefix):-len(suffix)]
        parts = core.split('_')
        if len(parts) >= 3: # e.g., device_location_type or device_location1_location2_type
            device_id = parts[0]
            device_type = ''.join(filter(str.isalpha, device_id)) # Heuristic for device type
            
            # Try to determine if the last part is a type_suffix (like re0, re1)
            potential_type_suffix = parts[-1]
            # A simple check: if it contains numbers or is 're0'/'re1', assume it's a type_suffix
            if any(char.isdigit() for char in potential_type_suffix) or potential_type_suffix in ["re0", "re1"]:
                type_suffix = potential_type_suffix
                location = '_'.join(parts[1:-1]) # Everything between device_id and type_suffix
            else:
                type_suffix = None # No clear type_suffix found by this logic
                location = '_'.join(parts[1:]) # Everything after device_id is location
            return device_type, device_id, location, type_suffix
    # Fallback for names not matching the pattern
    parts = name.split('_')
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2], None # Basic split
    return "unknown", "unknown", "unknown", None


def setup_qdrant():
    logger.info("Verifying Qdrant collections...")
    for collection_name in AVAILABLE_COLLECTIONS:
        try:
            qdrant.get_collection(collection_name=collection_name)
            # logger.info(f"Collection '{collection_name}' found.") # Too verbose for startup
        except Exception: # Broad exception as in original, specific Qdrant exceptions are better
            # This means the collection does not exist or there's an error accessing it.
            # Original code created it if not found. Here we only log.
            # If creation is desired, it should be:
            # qdrant.recreate_collection(
            #     collection_name=collection_name,
            #     vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
            # )
            # logger.info(f"Collection '{collection_name}' created.")
            logger.warning(f"Collection '{collection_name}' listed in AVAILABLE_COLLECTIONS but not found in Qdrant.")
        except Exception as e: # Catch other errors during check
            logger.error(f"Error checking/setting up collection '{collection_name}': {e}")
    logger.info("Qdrant collection verification complete.")