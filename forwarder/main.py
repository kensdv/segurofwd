import asyncio
from telethon import TelegramClient
from forwarder.utils.config_loader import load_config
from forwarder.utils.mongo import get_users_collection
from forwarder.handlers.message_handler import forward_message
from forwarder.tasks.cleanup import clean_forwarded_cas

# Load configuration
config = load_config()
API_ID = config["api_id"]
API_HASH = config["api_hash"]

# MongoDB connection
users_collection = get_users_collection()

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
