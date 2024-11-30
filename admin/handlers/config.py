from aiogram import types, Dispatcher
from admin.utils.decorators import handle_exceptions, is_logged_in
from admin.utils.telegram import get_user_dialogs
from admin.utils.mongodb import get_or_create_user, update_user
from admin.templates.messages import (
    RESET_CONFIG_MESSAGE,
    INVALID_INPUT_MESSAGE,
    DESTINATION_GROUP_SET_MESSAGE,
    NO_GROUPS_FOUND_MESSAGE,
)
from admin.config import GROUPS_PER_PAGE


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
    # Reset user configuration in MongoDB
    update_user(user_id, {"destination_group_id": None, "trading_bot_id": None})
    await message.reply(RESET_CONFIG_MESSAGE)


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

    group_id_or_username = args[1]
    try:
        # Update the user's destination group ID
        update_user(user_id, {"destination_group_id": group_id_or_username})
        await message.reply(DESTINATION_GROUP_SET_MESSAGE.format(group_id=group_id_or_username))
    except Exception as e:
        await message.reply(f"❌ Error setting destination group: {e}")


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


def register_config_handlers(dp: Dispatcher):
    """
    Register configuration-related command handlers with the dispatcher.
    """
    dp.register_message_handler(view_config_command, commands=["view_config"])
    dp.register_message_handler(reset_config_command, commands=["reset_config"])
    dp.register_message_handler(set_destination_command, commands=["set_destination"])
    dp.register_message_handler(list_groups_command, commands=["list_groups"])