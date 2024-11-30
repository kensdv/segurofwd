import time
from .constants import TIME_THRESHOLD
from .db import group_configs_collection

# Cache to track forwarded contract addresses with timestamps
forwarded_cas = {}

def fetch_user_config(user_id):
    """
    Retrieve user-specific configuration from MongoDB.

    Args:
        user_id (str): The ID of the user.

    Returns:
        tuple: A tuple containing two dictionaries:
            - group_notifiers (dict): Mapping of group IDs to their notifiers.
            - notifier_keys (dict): Mapping of notifier names to their keys.
    """
    groups = group_configs_collection.find({"user_id": user_id})
    group_notifiers = {group["group_id"]: group["notifier"] for group in groups}
    notifier_keys = {group["notifier"]: group["notifier_key"] for group in groups}
    return group_notifiers, notifier_keys

def round_to_k(value):
    """
    Round large numeric values to the nearest thousand and append 'k'.

    Args:
        value (str): A numeric value as a string, potentially containing commas.

    Returns:
        str: The value rounded to the nearest thousand, followed by 'k'.
    """
    try:
        value = float(value.replace(",", ""))
        return f"{round(value / 1000)}k"
    except ValueError:
        raise ValueError(f"Invalid number format: {value}")

def track_forwarded_address(contract_address):
    """
    Track forwarded contract addresses to prevent duplicates.

    Args:
        contract_address (str): The contract address to track.

    Returns:
        bool: True if the address is new and successfully tracked, False if it was already tracked.
    """
    current_time = time.time()
    if contract_address in forwarded_cas:
        return False
    forwarded_cas[contract_address] = current_time
    return True

def cleanup_forwarded_cas():
    """
    Clean up old entries from the forwarded_cas cache.

    Removes entries that exceed the time threshold defined in TIME_THRESHOLD.
    """
    current_time = time.time()
    to_remove = [address for address, timestamp in forwarded_cas.items()
                 if current_time - timestamp > TIME_THRESHOLD]
    for address in to_remove:
        del forwarded_cas[address]
