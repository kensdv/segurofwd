import time
import logging
import asyncio
from .helpers import forwarded_cas
from .constants import TIME_THRESHOLD

async def clean_forwarded_cas():
    """Periodically clean up old forwarded contract addresses."""
    while True:
        try:
            current_time = time.time()
            to_remove = [address for address, timestamp in forwarded_cas.items() 
                         if current_time - timestamp > TIME_THRESHOLD]

            for address in to_remove:
                del forwarded_cas[address]

            logging.info(f"Cleaned {len(to_remove)} old addresses from forwarded_cas.")
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
        await asyncio.sleep(86400)  # Run every 24 hours
