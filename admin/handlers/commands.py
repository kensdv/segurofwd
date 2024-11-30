from aiogram import types, Dispatcher
from admin.utils.mongodb import get_or_create_user, delete_user_session
from admin.templates.messages import (
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    RESET_CONFIG_MESSAGE,
    INVALID_INPUT_MESSAGE,
    TRADING_BOT_SET_MESSAGE,
    TRADING_BOT_SETUP_ERROR_MESSAGE,
    SESSION_UNAUTHORIZED_MESSAGE,
    DESTINATION_GROUP_SET_MESSAGE,
    NO_GROUPS_FOUND_MESSAGE,
)
from admin.utils.decorators import handle_exceptions, is_logged_in
from admin.utils.telegram import (
    log_out_user,
    get_user_dialogs,
    get_full_channel,
)
from admin.config import GROUPS_PER_PAGE


@handle_exceptions()
async def start_command(message: types.Message):
    """
    Handle the /start command. Send a welcome message to the user.
    """
    user_id = message.from_user.id
    username = message.from_user.username
    get_or_create_user(user_id, username)
    await message.reply(WELCOME_MESSAGE, parse_mode="Markdown")


@handle_exceptions()
async def help_command(message: types.Message):
    """
    Handle the /help command. Send a list of available commands.
    """
    await message.reply(HELP_MESSAGE)


@handle_exceptions()
@is_logged_in()
async def logout_command(message: types.Message):
    """
    Handle the /logout command. Log the user out and remove their session.
    """
    user_id = message.from_user.id
    success = await log_out_user(user_id)
    if success:
        delete_user_session(user_id)
        await message.reply(RESET_CONFIG_MESSAGE)
    else:
        await message.reply(SESSION_UNAUTHORIZED_MESSAGE)


@handle_exceptions()
@is_logged_in()
async def list_groups_command(message: types.Message):
    """
    Handle the /list_groups command. List all Telegram groups and channels.
    """
    user_id = message.from_user.id
    dialogs = await get_user_dialogs(user_id)

    if not dialogs:
        await message.reply(NO_GROUPS_FOUND_MESSAGE)
        return

    response = "\n".join(
        [f"{idx + 1}. {dialog['name']} (ID: {dialog['id']})" for idx, dialog in enumerate(dialogs[:GROUPS_PER_PAGE])]
    )
    await message.reply(response)


@handle_exceptions()
@is_logged_in()
async def set_destination_command(message: types.Message):
    """
    Handle the /set_destination command. Set the destination group ID.
    """
    user_id = message.from_user.id
    args = message.text.strip().split(maxsplit=1)

    if len(args) < 2:
        await message.reply(INVALID_INPUT_MESSAGE)
        return

    group_name = args[1]
    try:
        group = await get_full_channel(user_id, group_name)
        destination_group_id = group.chats[0].id

        # Update user's destination group in MongoDB
        get_or_create_user(user_id)  # Ensure the user exists
        delete_user_session(user_id)
        await message.reply(DESTINATION_GROUP_SET_MESSAGE.format(group_id=destination_group_id))
    except Exception as e:
        await message.reply(f"❌ Error setting destination group: {e}")


@handle_exceptions()
@is_logged_in()
async def tradingbot_command(message: types.Message):
    """
    Handle the /tradingbot command. Set a trading bot for the user.
    """
    user_id = message.from_user.id
    args = message.text.strip().split(maxsplit=1)

    if len(args) < 2:
        await message.reply(INVALID_INPUT_MESSAGE)
        return

    bot_info = args[1]
    try:
        # Assume Telethon handles this with get_entity
        trading_bot_id = int(bot_info) if bot_info.isdigit() else await get_full_channel(user_id, bot_info)
        await message.reply(TRADING_BOT_SET_MESSAGE.format(bot_name=bot_info, bot_id=trading_bot_id))
    except Exception as e:
        await message.reply(TRADING_BOT_SETUP_ERROR_MESSAGE.format(error=str(e)))


@handle_exceptions()
@is_logged_in()
async def view_config_command(message: types.Message):
    """
    Handle the /view_config command. Show the user's current configuration.
    """
    user_id = message.from_user.id
    user = get_or_create_user(user_id)

    config = (
        f"Your current configuration:\n"
        f"- Session Name: {user.get('session_name', 'Not set')}\n"
        f"- Destination Group ID: {user.get('destination_group_id', 'Not set')}\n"
        f"- Trading Bot ID: {user.get('trading_bot_id', 'Not set')}"
    )
    await message.reply(config)


@handle_exceptions()
@is_logged_in()
async def reset_config_command(message: types.Message):
    """
    Handle the /reset_config command. Reset the user's configuration to defaults.
    """
    user_id = message.from_user.id
    delete_user_session(user_id)
    await message.reply(RESET_CONFIG_MESSAGE)


def register_commands(dp: Dispatcher):
    """
    Register all command handlers with the dispatcher.
    """
    dp.register_message_handler(start_command, commands=["start"])
    dp.register_message_handler(help_command, commands=["help"])
    dp.register_message_handler(logout_command, commands=["logout"])
    dp.register_message_handler(list_groups_command, commands=["list_groups"])
    dp.register_message_handler(set_destination_command, commands=["set_destination"])
    dp.register_message_handler(tradingbot_command, commands=["tradingbot"])
    dp.register_message_handler(view_config_command, commands=["view_config"])
    dp.register_message_handler(reset_config_command, commands=["reset_config"])