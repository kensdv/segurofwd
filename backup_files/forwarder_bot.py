# bot.py

import json
import logging
import re
import time
import asyncio
from telethon import TelegramClient, events
from pymongo import MongoClient

# Load configuration from config.json
with open("config.json", "r") as config_file:
    config = json.load(config_file)

API_ID = config["api_id"]
API_HASH = config["api_hash"]
MONGO_URI = config["mongo_uri"]  # Include MongoDB URI in config.json if needed

# MongoDB connection
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['kaoru']
users_collection = db['users']
group_configs_collection = db['group_configs']

# Solana address pattern
solana_address_pattern = r'\b[a-zA-Z0-9]{32,44}\b'
TIME_THRESHOLD = 86400  # 24 hours in seconds

# Set up logging
logging.basicConfig(level=logging.WARNING)

# Dictionary to track forwarded contract addresses
forwarded_cas = {}

# Function to fetch user-specific configurations from MongoDB
def fetch_user_config(user_id):
    user = users_collection.find_one({"_id": user_id})
    if not user:
        return None, None, {}, {}
    groups = group_configs_collection.find({"user_id": user_id})
    group_notifiers = {group['group_id']: group['notifier'] for group in groups}
    notifier_keys = {group['notifier']: group['notifier_key'] for group in groups}
    return user['destination_group_id'], user['trading_bot_id'], group_notifiers, notifier_keys

# Function to round market cap values to the nearest thousand with 'k'
def round_to_k(value):
    value = float(value.replace(",", ""))
    return f"{round(value / 1000)}k"

# Function to periodically clean up old forwarded contract addresses
async def clean_forwarded_cas():
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
        await asyncio.sleep(86400)  # Run this check every 24 hours

# Message handler for new messages
@events.register(events.NewMessage)
async def forward_message(event):
    user_id = event.sender_id
    destination_group_id, trading_bot_id, group_notifiers, notifier_keys = fetch_user_config(user_id)

    # Skip processing if no destination group or group notifiers are configured
    if not destination_group_id or not group_notifiers:
        return

    try:
        message_text = event.message.message or ''
        group_id = str(event.chat_id)

        # Print incoming messages for debugging
        print(f"Incoming message from Group {group_id}, Sender {user_id}: {message_text}")

        # Extract token name, market cap, and contract address
        token_pattern = r"^(.*?) \| @"  # Extract token name
        mc_pattern = r"💹MC: \$([\d,]+\.\d+)"  # Extract market cap
        ca_pattern = r"CA: ([a-zA-Z0-9]{32,44})"  # Extract contract address

        token_match = re.search(token_pattern, message_text, re.MULTILINE)
        mc_match = re.search(mc_pattern, message_text)
        ca_match = re.search(ca_pattern, message_text)

        # Ensure matches are found
        if not token_match or not mc_match or not ca_match:
            print("Error: Unable to extract token name, market cap, or contract address.")
            return

        token_name = token_match.group(1).strip()
        market_cap = round_to_k(mc_match.group(1))  # Rounded market cap
        contract_address = ca_match.group(1)

        # Filter out addresses already forwarded
        current_time = time.time()
        if contract_address in forwarded_cas:
            print("No new Solana address or keywords found.")
            return

        # Track forwarded address with the current timestamp
        forwarded_cas[contract_address] = current_time

        # Get the notifier key for the group ID
        notifier = group_notifiers.get(group_id, 'Insider Play')
        notifier_key = notifier_keys.get(notifier, '1')

        # Prepare the forwarding message with the token name and market cap
        forward_message = f"{notifier}\n\n"
        forward_message += f"{token_name}\n"  # Include token name
        forward_message += f"MC: {market_cap}\n\n"  # Include market cap
        forward_message += f"{contract_address}\n\n"
        forward_message += "🤖 Ape Faster, Use bot below:\n"
        forward_message += f"[Trojan](https://t.me/helenus_trojanbot?start=r-kaoru9-{contract_address}) | "
        forward_message += f"[Maestro](https://t.me/MaestroSniperBot?start={contract_address}-kaoru91819) | "
        forward_message += f"[Bonk Bot](https://t.me/bonkbot_bot?start=ref_fnhex_ca_{contract_address}) | "
        forward_message += f"[STB](https://t.me/SolTradingBot_Europe_Bot?start={contract_address}-lUNqcvksz)\n\n"

        # Send message to destination group
        await event.client.send_message(destination_group_id, forward_message, parse_mode="Markdown")
        print(f"Forwarded message with CA: {contract_address} and dynamic referral links to the destination group.")

        # Send message to trading bot
        if trading_bot_id:
            await event.client.send_message(trading_bot_id, forward_message, parse_mode="Markdown")
            print(f"Forwarded message with CA: {contract_address} to the trading bot.")
    except Exception as e:
        print(f"Error: {e}")

# Main function to start the bot
async def main():
    clients = []

    # Fetch all users with session files
    users = users_collection.find({})
    for user in users:
        session_name = user['session_name']
        client = TelegramClient(session_name, API_ID, API_HASH)
        await client.start()

        # Add message handler for the user client
        client.add_event_handler(forward_message)
        clients.append(client)

    print("Bots are running, listening for messages...")
    try:
        await asyncio.gather(*[client.run_until_disconnected() for client in clients], clean_forwarded_cas())
    except KeyboardInterrupt:
        print("Shutting down gracefully...")
        for client in clients:
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
