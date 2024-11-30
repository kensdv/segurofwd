import re
import time
from telethon import events
from .helpers import fetch_user_config, forwarded_cas, round_to_k, track_forwarded_address

@events.register(events.NewMessage)
async def forward_message(event):
    """
    Handles new messages and forwards them based on user configuration.

    Args:
        event (telethon.events.newmessage.NewMessage.Event): Event triggered by a new message.
    """
    user_id = event.sender_id

    try:
        # Fetch user-specific configurations
        group_notifiers, notifier_keys = fetch_user_config(user_id)

        # Extract message content and group ID
        message_text = event.message.message or ""
        group_id = str(event.chat_id)

        # Debugging: Print incoming message details
        print(f"Incoming message from Group {group_id}, Sender {user_id}: {message_text}")

        # Define patterns to extract token name, market cap, and contract address
        token_pattern = r"^(.*?) \| @"  # Extract token name
        mc_pattern = r"💹MC: \$([\d,]+\.\d+)"  # Extract market cap
        ca_pattern = r"CA: ([a-zA-Z0-9]{32,44})"  # Extract contract address

        # Perform regex matching
        token_match = re.search(token_pattern, message_text, re.MULTILINE)
        mc_match = re.search(mc_pattern, message_text)
        ca_match = re.search(ca_pattern, message_text)

        # Ensure all required details are present
        if not token_match or not mc_match or not ca_match:
            print("Error: Unable to extract token name, market cap, or contract address.")
            return

        # Extract values
        token_name = token_match.group(1).strip()
        market_cap = round_to_k(mc_match.group(1))
        contract_address = ca_match.group(1)

        # Check if the contract address is already forwarded
        if not track_forwarded_address(contract_address):
            print("No new Solana address or keywords found.")
            return

        # Retrieve notifier and notifier key
        notifier = group_notifiers.get(group_id, "Insider Play")
        notifier_key = notifier_keys.get(notifier, "1")

        # Construct the forwarding message
        forward_message = (
            f"{notifier}\n\n"
            f"{token_name}\n"
            f"MC: {market_cap}\n\n"
            f"{contract_address}\n\n"
            "🤖 Ape Faster, Use bot below:\n"
            f"[Trojan](https://t.me/helenus_trojanbot?start=r-kaoru9-{contract_address}) | "
            f"[Maestro](https://t.me/MaestroSniperBot?start={contract_address}-kaoru91819) | "
            f"[Bonk Bot](https://t.me/bonkbot_bot?start=ref_fnhex_ca_{contract_address}) | "
            f"[STB](https://t.me/SolTradingBot_Europe_Bot?start={contract_address}-lUNqcvksz)\n\n"
        )

        # Forward the constructed message to the user
        await event.client.send_message(user_id, forward_message, parse_mode="Markdown")
        print(f"Forwarded message with CA: {contract_address}.")
    except Exception as e:
        # Log the exception for debugging
        print(f"Error: {e}")
