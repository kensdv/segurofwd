from aiogram import types, Dispatcher, Bot
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from admin.utils.sessions import MongoSession
from admin.utils.mongodb import get_or_create_user, users_collection
from admin.config import API_ID, API_HASH, CUSTOM_FOLDER
from typing import Dict
import os

# In-memory storage for pending login states
pending_logins: Dict[int, Dict] = {}

# Ensure the session folder exists
if not os.path.exists(CUSTOM_FOLDER):
    os.makedirs(CUSTOM_FOLDER)


async def start_login(message: types.Message):
    """
    Start the login process by asking for the user's phone number.
    """
    user_id = message.from_user.id
    username = message.from_user.username
    user = get_or_create_user(user_id, username)

    # Check if the user is already logged in
    if "session_name" in user:
        await message.reply("✅ You are already logged in. Use /logout to log out.")
        return

    # Request phone number
    await message.reply("📱 Please send your phone number to log in (e.g., +123456789).")
    pending_logins[user_id] = {"client": None, "phone": None, "awaiting_otp": False, "awaiting_password": False}


async def handle_phone_number(message: types.Message):
    """
    Handle the phone number provided by the user for login.
    """
    user_id = message.from_user.id
    phone_number = message.text.strip()

    # Validate phone number format
    if not phone_number.startswith("+") or not phone_number[1:].isdigit():
        await message.reply("❌ Invalid phone number. Please use the format +123456789.")
        return

    # Use MongoSession for Telethon
    session = MongoSession(user_id)
    client = TelegramClient(session, API_ID, API_HASH)
    pending_logins[user_id].update({"client": client, "phone": phone_number, "awaiting_otp": True})

    await client.connect()

    try:
        # Send code request
        await client.send_code_request(phone_number)
        await message.reply("🔑 An OTP has been sent to your Telegram account. Please send the OTP as it appears.")
    except FloodWaitError as e:
        await message.reply(f"❌ Too many attempts. Please retry after {e.seconds} seconds.")
        pending_logins.pop(user_id, None)
    except Exception as e:
        await message.reply(f"❌ Failed to send OTP: {e}")
        pending_logins.pop(user_id, None)


async def handle_otp(message: types.Message):
    """
    Handle the OTP provided by the user.
    """
    user_id = message.from_user.id
    otp = message.text.strip()

    # Validate OTP format
    if not otp.isdigit():
        await message.reply("❌ Invalid OTP format. Please send the OTP as a numeric value.")
        return

    # Ensure the user is in the pending logins state
    if user_id not in pending_logins or not pending_logins[user_id].get("awaiting_otp"):
        await message.reply("⚠️ No OTP requested. Please use /login to start the process.")
        return

    client = pending_logins[user_id]["client"]
    phone_number = pending_logins[user_id]["phone"]

    try:
        # Attempt login
        await client.sign_in(phone=phone_number, code=otp)

        # Save session to MongoDB
        users_collection.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "session_name": f"{CUSTOM_FOLDER}/session_{user_id}",
                    "phone_number": phone_number
                }
            },
            upsert=True
        )
        pending_logins.pop(user_id, None)
        await message.reply("✅ Login successful! You can now use the bot.")
    except SessionPasswordNeededError:
        # Handle 2FA
        pending_logins[user_id]["awaiting_password"] = True
        pending_logins[user_id]["awaiting_otp"] = False
        await message.reply("🔒 Your account is protected with 2FA. Please send your password.")
    except Exception as e:
        pending_logins.pop(user_id, None)
        await message.reply(f"❌ Login failed: {e}")


async def handle_2fa_password(message: types.Message):
    """
    Handle the 2FA password provided by the user.
    """
    user_id = message.from_user.id
    password = message.text.strip()

    # Ensure the user is in the pending password state
    if user_id not in pending_logins or not pending_logins[user_id].get("awaiting_password"):
        await message.reply("⚠️ No password required at this time.")
        return

    client = pending_logins[user_id]["client"]

    try:
        # Attempt 2FA login
        await client.sign_in(password=password)

        # Save session to MongoDB
        phone_number = pending_logins[user_id]["phone"]
        users_collection.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "session_name": f"{CUSTOM_FOLDER}/session_{user_id}",
                    "phone_number": phone_number
                }
            },
            upsert=True
        )
        pending_logins.pop(user_id, None)
        await message.reply("✅ Login successful with 2FA! You can now use the bot.")
    except Exception as e:
        pending_logins.pop(user_id, None)
        await message.reply(f"❌ 2FA Login failed: {e}")


def register_login_handlers(dp: Dispatcher):
    """
    Register login-related command handlers with the dispatcher.
    """
    dp.register_message_handler(start_login, commands=["login"])
    dp.register_message_handler(
        handle_phone_number,
        lambda msg: msg.from_user.id in pending_logins and not pending_logins[msg.from_user.id].get("phone")
    )
    dp.register_message_handler(
        handle_otp,
        lambda msg: msg.from_user.id in pending_logins and pending_logins[msg.from_user.id].get("awaiting_otp")
    )
    dp.register_message_handler(
        handle_2fa_password,
        lambda msg: msg.from_user.id in pending_logins and pending_logins[msg.from_user.id].get("awaiting_password")
    )
