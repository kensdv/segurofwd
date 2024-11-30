import logging
from aiogram import Bot, Dispatcher, executor
from aiogram.types import BotCommand
from admin.config import API_TOKEN
from admin.handlers.login import register_login_handlers
from admin.handlers.groups import register_group_handlers
from admin.handlers.commands import register_command_handlers

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Bot and Dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


async def set_bot_commands():
    """
    Set bot commands for the user interface.
    """
    commands = [
        BotCommand(command="/start", description="Start the bot"),
        BotCommand(command="/help", description="Show help"),
        BotCommand(command="/login", description="Login to your account"),
        BotCommand(command="/logout", description="Log out of your account"),
        BotCommand(command="/list_groups", description="List your Telegram groups"),
        BotCommand(command="/set_destination", description="Set a destination group"),
        BotCommand(command="/set_notifier", description="Assign a notifier to a group"),
        BotCommand(command="/tradingbot", description="Set up a trading bot"),
        BotCommand(command="/view_config", description="View your configuration"),
        BotCommand(command="/reset_config", description="Reset your configuration"),
    ]
    await bot.set_my_commands(commands)


async def on_startup(dispatcher: Dispatcher):
    """
    Perform startup tasks such as setting bot commands.
    """
    logger.info("Starting bot...")
    await set_bot_commands()
    logger.info("Bot commands set successfully.")


def main():
    """
    Main function to start the bot.
    """
    # Register handlers
    register_login_handlers(dp)
    register_group_handlers(dp, bot)
    register_command_handlers(dp)

    # Start polling
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)


if __name__ == "__main__":
    main()
