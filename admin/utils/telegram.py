from telethon import TelegramClient
from telethon.errors import FloodWaitError, UnauthorizedError
from telethon.tl.functions.channels import GetFullChannelRequest
from admin.utils.sessions import MongoSession
from admin.config import API_ID, API_HASH
import logging

async def with_telegram_client(user_id: int, coro):
    """
    Safely execute a coroutine with a TelegramClient using MongoDB-based session.

    Args:
        user_id (int): The Telegram user ID.
        coro (callable): The coroutine to execute with the TelegramClient.

    Returns:
        Any: The result of the coroutine.

    Raises:
        Exception: If any error occurs during client operation.
    """
    session = MongoSession(user_id)
    client = TelegramClient(session, API_ID, API_HASH)
    await client.connect()
    try:
        return await coro(client)
    finally:
        await client.disconnect()

async def get_full_channel(user_id: int, channel_name: str):
    """
    Retrieve full channel details using the Telethon client.

    Args:
        user_id (int): The Telegram user ID.
        channel_name (str): The channel's username (e.g., "@channelname").

    Returns:
        telethon.tl.types.ChannelFull: The full channel details.

    Raises:
        Exception: If an error occurs while fetching channel details.
    """
    async def fetch_channel(client):
        return await client(GetFullChannelRequest(channel_name))

    return await with_telegram_client(user_id, fetch_channel)

async def get_user_dialogs(user_id: int):
    """
    Retrieve the user's dialogs (chats, groups, and channels).

    Args:
        user_id (int): The Telegram user ID.

    Returns:
        List[dict]: A list of dictionaries containing dialog information.
    """
    async def fetch_dialogs(client):
        dialogs = await client.get_dialogs()
        return [
            {"id": dialog.id, "name": dialog.name, "is_group": dialog.is_group, "is_channel": dialog.is_channel}
            for dialog in dialogs
        ]

    return await with_telegram_client(user_id, fetch_dialogs)

async def send_code_request(user_id: int, phone_number: str):
    """
    Send a login code to the user's phone number.

    Args:
        user_id (int): The Telegram user ID.
        phone_number (str): The user's phone number.

    Raises:
        Exception: If an error occurs while sending the code.
    """
    async def send_code(client):
        return await client.send_code_request(phone_number)

    return await with_telegram_client(user_id, send_code)

async def sign_in_with_code(user_id: int, phone_number: str, code: str):
    """
    Sign in the user using the provided phone number and login code.

    Args:
        user_id (int): The Telegram user ID.
        phone_number (str): The user's phone number.
        code (str): The login code sent to the user.

    Returns:
        telethon.tl.types.User: The authenticated user.

    Raises:
        Exception: If login fails.
    """
    async def sign_in(client):
        return await client.sign_in(phone=phone_number, code=code)

    return await with_telegram_client(user_id, sign_in)

async def log_out_user(user_id: int):
    """
    Log out the user from the Telegram account.

    Args:
        user_id (int): The Telegram user ID.

    Returns:
        bool: True if successful, False otherwise.
    """
    async def log_out(client):
        return await client.log_out()

    try:
        await with_telegram_client(user_id, log_out)
        return True
    except UnauthorizedError:
        logging.warning(f"User {user_id} was already unauthorized.")
        return False
