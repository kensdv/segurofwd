import logging
from functools import wraps
from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware
from telethon.errors import UnauthorizedError
from admin.utils.mongodb import users_collection

def is_logged_in():
    """
    Decorator to check if a user is logged in before processing a command.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(message: types.Message, *args, **kwargs):
            user_id = message.from_user.id
            user = users_collection.find_one({"_id": user_id})
            if not user or "session_name" not in user:
                await message.reply("⚠️ You must log in first using /login.")
                return
            return await func(message, *args, **kwargs)
        return wrapper
    return decorator

def handle_exceptions():
    """
    Decorator to handle exceptions and log errors gracefully.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except UnauthorizedError:
                logging.error("Unauthorized error: User session is not authorized.")
                await args[0].reply("⚠️ Session unauthorized. Please log in again.")
            except Exception as e:
                logging.error(f"Unexpected error in {func.__name__}: {e}")
                await args[0].reply(f"❌ Unexpected error occurred: {e}")
        return wrapper
    return decorator

class LoggingMiddleware(BaseMiddleware):
    """
    Middleware to log incoming updates for debugging purposes.
    """
    async def on_pre_process_update(self, update, data):
        logging.info(f"Received update: {update}")
