import logging
import asyncio
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.functions.channels import GetFullChannelRequest
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from telethon.sessions import MemorySession
from typing import Dict, List
from dotenv import load_dotenv
from telethon.sessions import StringSession
import json
import os

# Load sensitive credentials from .env
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")

# Initialize bot, dispatcher, and MongoDB client
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['kaoru']
users_collection = db['users']
group_configs_collection = db['group_configs']

# Temporary in-memory storage for login states
pending_logins: Dict[int, Dict] = {}
selected_groups = {}  # Initialize a dictionary to store selected groups per user
LOGIN_TIMEOUT = 300  # Timeout for stale login sessions (5 minutes)
MAX_OTP_RETRIES = 3
GROUPS_PER_PAGE = 10

# Cutstom Folder for sessions
custom_folder = 'sessions'
if not os.path.exists(custom_folder):
    os.makedirs(custom_folder)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Helper: Check Login Status
def is_logged_in(user_id: int) -> bool:
    user = users_collection.find_one({"_id": user_id})
    return bool(user and user.get("session_name"))

def get_client(user_id: int) -> TelegramClient:
    session_name = f"session_{user_id}"
    client = TelegramClient(session_name, API_ID, API_HASH)
    return client

# Custom MongoDB-based Telethon Session
class MongoSession(StringSession):
    def __init__(self, user_id, db):
        super().__init__()
        self.user_id = user_id
        self.db = db
        self.load()

    def save(self):
        session_data = self.save_to_string()  # Convert session to string
        self.db.sessions.update_one(
            {"user_id": self.user_id},
            {"$set": {"session_data": session_data}},
            upsert=True
        )

    def load(self):
        session_entry = self.db.sessions.find_one({"user_id": self.user_id})
        if session_entry:
            self.load_from_string(session_entry["session_data"])

    def save_to_string(self):
        return self.save()

    def load_from_string(self, session_str):
        self.set_dc(self.dc_id, self.server_address, self.port)
        super().load(session_str)




# Helper: Create or retrieve a user from MongoDB
def get_or_create_user(user_id: int, username: str = None) -> Dict:
    user = users_collection.find_one({"_id": user_id})
    if not user:
        # Create a new user if it doesn't exist
        user = {
            "_id": user_id,
            "username": username,
            "source_group_ids": [],
            "destination_group_id": None,
            "trading_bot_id": None,
        }
        users_collection.insert_one(user)
    else:
        # Update username if it's different or missing
        if username and user.get("username") != username:
            users_collection.update_one({"_id": user_id}, {"$set": {"username": username}})
            user["username"] = username  # Reflect the updated username in the returned object
    return user


# Command Start
@dp.message_handler(commands=["start"])
async def start_command(message: types.Message) -> None:
    user_id = message.from_user.id
    username = message.from_user.username  # Extract the username
    get_or_create_user(user_id, username)  # Pass the username to the helper
    
    welcome_message = (
        "👋 Welcome to **Seguro Fwd Bot – Test Edition!**\n\n"
        "⚙️ **Features:**\n"
        "- 🔐 Secure login process\n"
        "- 🔍 Seamless tracking of groups and listening for CA\n"
        "- 💼 24/7 forwarding for CA from selected group/channel\n"
        "- ⏳ Forwards CA to your trading bot for Autobuys\n"
        "- 👩‍💻 Fully user control based\n\n"
        "📢 **Stay Updated:**\n"
        "DM @kensgx for essential updates/enquiries.\n\n"
        "Use /help to see all available commands"
    )
    
    await message.reply(welcome_message, parse_mode="Markdown")




# Command: Help
@dp.message_handler(commands=["help"])
async def help_command(message: types.Message) -> None:
    response = (
        "Available commands:\n"
        "/login - Login your account\n"
        "/help - Show available commands\n"
        "/logout - Log out\n"
        "/list_groups - List all your Telegram groups and channels\n"
        "/set_destination - Set the destination group ID\n"
        "/tradingbot - Set Trading bot\n"
        "/set_notifier - Assign a notifier to a group\n"
        "/view_config - View your current configuration\n"
        "/reset_config - Reset all your configuration to default\n"
    )
    await message.reply(response)


# Helper: Exponential Backoff Retry
async def retry_with_backoff(method, retries=5, delay=3):
    for attempt in range(retries):
        try:
            return await method()
        except FloodWaitError as e:
            wait_time = e.retry_after or delay * (2 ** attempt)
            logging.warning(f"Flood control triggered. Retrying in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
        except Exception as e:
            logging.error(f"Unexpected error in retry: {e}")
            raise
    raise Exception("Max retries exceeded.")


# Command: Login
@dp.message_handler(commands=['login'])
async def start_login(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    user = get_or_create_user(user_id, username)

    if "session_name" in user:
        await message.reply("You are already logged in. Use /logout to log out.")
        return

    await message.reply("Please send your phone number to log in (e.g., +123456789).")
    pending_logins[user_id] = {"client": None, "phone": None, "awaiting_otp": False, "awaiting_password": False}

# Handle Phone Number
@dp.message_handler(lambda message: message.from_user.id in pending_logins and not pending_logins[message.from_user.id].get("phone"))
async def handle_phone_number(message: types.Message):
    user_id = message.from_user.id
    phone_number = message.text.strip()

    # Use MongoSession for session storage
    session = MongoSession(user_id, db)
    client = TelegramClient(session, API_ID, API_HASH)
    pending_logins[user_id].update({"client": client, "phone": phone_number, "awaiting_otp": True})

    await client.connect()

    try:
        await client.send_code_request(phone_number)
        await message.reply("An OTP has been sent to your Telegram account. Prepend 'XX' to the OTP and send it (e.g., 'XX12345').")
    except FloodWaitError as e:
        await message.reply(f"Too many attempts. Retry in {e.seconds} seconds.")
        del pending_logins[user_id]
    except Exception as e:
        await message.reply(f"Error: {e}")
        del pending_logins[user_id]





# Handler: Receive OTP
@dp.message_handler(lambda message: message.from_user.id in pending_logins and pending_logins[message.from_user.id]["awaiting_otp"])
async def handle_otp(message: types.Message):
    user_id = message.from_user.id
    otp_message = message.text.strip()

    if not otp_message.startswith("XX") or not otp_message[2:].isdigit():
        await message.reply("Invalid format! Please prepend 'XX' to the OTP and send it (e.g., 'XX12345').")
        return

    otp = otp_message[2:]  # Extract the OTP by stripping the "XX" prefix
    client = pending_logins[user_id]["client"]
    phone_number = pending_logins[user_id]["phone"]

    try:
        # Attempt to sign in with the OTP
        await client.sign_in(phone=phone_number, code=otp)

        # Save session to MongoDB
        users_collection.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "session_name": f"{custom_folder}/session_{user_id}",
                    "phone_number": phone_number
                }
            },
            upsert=True
        )
        del pending_logins[user_id]
        await message.reply("Login successful! You can now use the bot.")
    except SessionPasswordNeededError:
        # Handle 2FA if enabled
        pending_logins[user_id]["awaiting_password"] = True
        pending_logins[user_id]["awaiting_otp"] = False
        await message.reply("Your account is protected with 2FA. Please send your password.")
    except Exception as e:
        del pending_logins[user_id]
        await message.reply(f"Login failed: {e}")

# Handler: 2FA Password
@dp.message_handler(lambda message: message.from_user.id in pending_logins and pending_logins[message.from_user.id]["awaiting_password"])
async def handle_2fa_password(message: types.Message):
    user_id = message.from_user.id
    password = message.text.strip()
    client = pending_logins[user_id]["client"]

    try:
        await client.sign_in(password=password)

        # Save session to MongoDB
        phone_number = pending_logins[user_id]["phone"]
        users_collection.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "session_name": f"{custom_folder}/session_{user_id}",
                    "phone_number": phone_number
                }
            },
            upsert=True
        )
        del pending_logins[user_id]
        await message.reply("Login successful with 2FA! You can now use the bot.")
    except Exception as e:
        del pending_logins[user_id]
        await message.reply(f"2FA Login failed: {e}")

# Command: Logout
@dp.message_handler(commands=['logout'])
async def logout(message: types.Message):
    user_id = message.from_user.id
    user = users_collection.find_one({"_id": user_id})

    if not user or "session_name" not in user:
        await message.reply("You are not logged in.")
        return

    try:
        session = MongoSession(user_id, db)
        client = TelegramClient(session, API_ID, API_HASH)
        await client.connect()
        await client.log_out()
        await client.disconnect()

        users_collection.update_one({"_id": user_id}, {"$unset": {"session_name": ""}})
        await message.reply("You have been logged out successfully.")
    except Exception as e:
        await message.reply(f"Logout failed: {e}")

# Set Trading Bot
@dp.message_handler(commands=['tradingbot'])
async def set_trading_bot(message: types.Message):
    user_id = message.from_user.id
    user = get_or_create_user(user_id)

    try:
        # Extract bot username or numeric ID from the command
        args = message.text.strip().split(maxsplit=1)
        if len(args) < 2:
            await message.reply("Usage: /set_trading_bot <@bot_username or group_id>")
            return

        bot_info = args[1]
        session_name = user.get("session_name")
        if not session_name:
            await message.reply("You are not logged in. Please log in using /login before setting the trading bot.")
            return

        # Resolve the bot's username or group ID using Telethon
        async with TelegramClient(session_name, API_ID, API_HASH) as client:
            if bot_info.startswith("@"):
                entity = await client.get_entity(bot_info)
                trading_bot_id = entity.id
                trading_bot_name = bot_info
            else:
                trading_bot_id = int(bot_info)
                trading_bot_name = bot_info  # Fallback if no username is provided

        # Save trading bot information to MongoDB
        users_collection.update_one(
            {"_id": user_id},
            {"$set": {"trading_bot_id": trading_bot_id}},
            upsert=True
        )
        await message.reply(f"Trading bot set to: {trading_bot_name} (ID: {trading_bot_id})")
    except IndexError:
        await message.reply("Usage: /set_trading_bot <@bot_username or group_id>")
    except Exception as e:
        await message.reply(f"Error setting trading bot: {e}")

# Command: List Groups
@dp.message_handler(commands=["list_groups"])
async def list_groups(message: types.Message) -> None:
    user_id = message.from_user.id
    if not is_logged_in(user_id):
        await message.reply("⚠️ You must log in first using /login to access this command.")
        return

    try:
        user = users_collection.find_one({"_id": user_id})
        session_name = user["session_name"]
        
        async def fetch_groups(client):
            dialogs = await client.get_dialogs()
            return [{"name": chat.name, "id": chat.id} for chat in dialogs if chat.is_group or chat.is_channel]

        group_list = await with_telethon_client(session_name, fetch_groups)
        pending_logins[user_id] = {"groups": group_list}
        await send_group_page(message.chat.id, user_id, page=0)
    except Exception as e:
        await message.reply(f"❌ Unexpected error: {e}")




# Helper: Safely use Telethon client within a coroutine
async def with_telethon_client(session_name: str, coro):
    client = TelegramClient(session_name, API_ID, API_HASH)
    await client.connect()
    try:
        return await coro(client)
    finally:
        await client.disconnect()



# Helper: Send Group Page
async def send_group_page(chat_id: int, user_id: int, page: int) -> None:
    # Check if user data exists
    if user_id not in pending_logins or "groups" not in pending_logins[user_id]:
        await bot.send_message(chat_id, "⚠️ No groups found. Please use /list_groups to refresh.")
        return

    group_list = pending_logins[user_id]["groups"]
    total_pages = (len(group_list) + GROUPS_PER_PAGE - 1) // GROUPS_PER_PAGE

    # Validate page
    if page < 0 or page >= total_pages:
        await bot.send_message(chat_id, "⚠️ Invalid page number.")
        return

    # Paginate groups
    start_idx, end_idx = page * GROUPS_PER_PAGE, (page + 1) * GROUPS_PER_PAGE
    groups_to_display = group_list[start_idx:end_idx]

    # Create markup
    markup = InlineKeyboardMarkup(row_width=4)

    # Add groups as buttons
    for group in groups_to_display:
        toggle_state = "❌" if group["id"] in selected_groups else "✅"
        button_label = f"{toggle_state} {group['name']}"
        markup.add(InlineKeyboardButton(button_label, callback_data=f"toggle_group:{group['id']}:{page}"))

    # Add "Search" and "Return" buttons (above the grid)
    markup.row(
        InlineKeyboardButton("Search", callback_data="search_groups"),
        InlineKeyboardButton("Return", callback_data="return_to_menu"),
    )

    # Pagination buttons (below the grid)
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"navigate:{page - 1}"))
    pagination_buttons.append(InlineKeyboardButton(f"Page {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"navigate:{page + 1}"))
    markup.row(*pagination_buttons)

    # Send the message with the markup
    await bot.send_message(chat_id, "Select call channels you'd like to subscribe to! 🔔", reply_markup=markup)

# Callback: Handle Group Toggling
@dp.callback_query_handler(lambda call: call.data.startswith("toggle_group"))
async def toggle_group(call: types.CallbackQuery):
    _, group_id, page = call.data.split(":")
    page = int(page)

    # Toggle the group selection
    user_id = call.from_user.id
    if user_id in pending_logins and group_id in pending_logins[user_id]["groups"]:
        if group_id in selected_groups:
            selected_groups.remove(group_id)
        else:
            selected_groups.add(group_id)

    # Refresh the current page
    await send_group_page(call.message.chat.id, user_id, page)


@dp.callback_query_handler(lambda call: call.data.startswith("navigate"))
async def navigate_page(call: types.CallbackQuery):
    _, page = call.data.split(":")
    page = int(page)

    # Go to the requested page
    user_id = call.from_user.id
    await send_group_page(call.message.chat.id, user_id, page)


# Command: Set Destination Group
@dp.message_handler(commands=['set_destination'])
async def set_destination(message: types.Message) -> None:
    user_id = message.from_user.id
    if not is_logged_in(user_id):
        await message.reply("⚠️ You must log in first using /login to access this command.")
        return

    args = message.text.strip().split(maxsplit=1)
    if len(args) < 2:
        await message.reply("❌ Usage: /set_destination <group_id or @group_username>")
        return

    group_name = args[1]
    session_name = users_collection.find_one({"_id": user_id})["session_name"]

    async with TelegramClient(session_name, API_ID, API_HASH) as client:
        try:
            if group_name.startswith("@"):
                group_entity = await client(GetFullChannelRequest(group_name))
                destination_group_id = group_entity.chats[0].id
            else:
                destination_group_id = int(group_name)

            users_collection.update_one(
                {"_id": user_id},
                {"$set": {"destination_group_id": destination_group_id}},
                upsert=True
            )
            await message.reply(f"✅ Destination group set to ID: {destination_group_id}")
        except ValueError:
            await message.reply("❌ Invalid input. Provide a group ID or a username starting with '@'.")
        except Exception as e:
            await message.reply(f"❌ Error setting destination group: {e}")



# Command: Set Notifier Group
@dp.message_handler(commands=['set_notifier'])
async def set_notifier(message: types.Message):
    user_id = message.from_user.id
    user = get_or_create_user(user_id)

    try:
        # Extract notifier name and associated source ID from the message
        args = message.text.strip().split(maxsplit=2)
        if len(args) < 3:
            await message.reply("Usage: /set_notifier <source_id> <notifier_name>")
            return

        source_id = int(args[1])
        notifier_name = args[2]

        # Check if source ID is in the user's selected groups
        if source_id not in user.get("source_group_ids", []):
            await message.reply("The provided source ID is not in your selected groups. Add it first using /list_groups.")
            return

        # Update or add the notifier name in the user's configuration
        group_configs_collection.update_one(
            {"_id": user_id, "source_group_ids": source_id},
            {"$set": {"notifier_name": notifier_name}},
            upsert=True
        )
        await message.reply(f"Notifier for source {source_id} set to: {notifier_name}")
    except ValueError:
        await message.reply("Invalid source ID. Please provide a numeric ID.")
    except Exception as e:
        await message.reply(f"Error setting notifier: {e}")

# Command: View Config
@dp.message_handler(commands=['view_config'])
async def view_config(message: types.Message):
    user_id = message.from_user.id
    user = get_or_create_user(user_id)

    config = f"""
        Your configuration:
        - Session Name: {user['session_name']}
        - Destination Group ID: {user['destination_group_id']}
        - Trading Bot ID: {user['trading_bot_id']}
    """
    await message.reply(config)

# Command: Reset Config
@dp.message_handler(commands=["reset_config"])
async def reset_config(message: types.Message):
    user_id = message.from_user.id
    users_collection.update_one(
        {"_id": user_id},
        {
            "$set": {
                "destination_group_id": None,
                "trading_bot_id": None
            }
        }
    )
    await message.reply("Configuration has been reset.")
    
    

# Main Entry Point
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)