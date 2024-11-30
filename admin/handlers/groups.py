from aiogram import types, Dispatcher, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from telethon import TelegramClient
from admin.utils.decorators import handle_exceptions, is_logged_in
from admin.utils.telegram import get_user_dialogs
from admin.utils.mongodb import get_or_create_user
from admin.templates.messages import (
    NO_GROUPS_FOUND_MESSAGE,
    INVALID_INPUT_MESSAGE,
    GROUP_PAGE_INSTRUCTION,
    INVALID_PAGE_NUMBER_MESSAGE,
)
from admin.config import API_ID, API_HASH, GROUPS_PER_PAGE

# In-memory storage for session data
pending_logins = {}
selected_groups = set()  # Use a set for efficient toggling


@handle_exceptions()
@is_logged_in()
async def list_groups_command(message: types.Message, bot: Bot):
    """
    Handle the /list_groups command. List all Telegram groups and channels with pagination.
    """
    user_id = message.from_user.id
    user = get_or_create_user(user_id)

    try:
        # Fetch groups using Telethon
        session_name = user.get("session_name")
        if not session_name:
            await message.reply("⚠️ You are not logged in. Please use /login to access this feature.")
            return

        async def fetch_groups(client):
            dialogs = await client.get_dialogs()
            return [{"name": chat.name, "id": chat.id} for chat in dialogs if chat.is_group or chat.is_channel]

        group_list = await with_telethon_client(session_name, fetch_groups)

        # Cache the groups in memory
        pending_logins[user_id] = {"groups": group_list}
        await send_group_page(bot, message.chat.id, user_id, page=0)

    except Exception as e:
        await message.reply(f"❌ Unexpected error: {e}")


@handle_exceptions()
async def toggle_group(call: types.CallbackQuery, bot: Bot):
    """
    Handle group toggling when a user selects/deselects a group.
    """
    _, group_id, page = call.data.split(":")
    page = int(page)

    user_id = call.from_user.id

    if user_id in pending_logins and "groups" in pending_logins[user_id]:
        if group_id in selected_groups:
            selected_groups.remove(group_id)
        else:
            selected_groups.add(group_id)

    # Refresh the group page
    await send_group_page(bot, call.message.chat.id, user_id, page)


@handle_exceptions()
async def navigate_page(call: types.CallbackQuery, bot: Bot):
    """
    Handle pagination when navigating between group list pages.
    """
    _, page = call.data.split(":")
    page = int(page)

    user_id = call.from_user.id
    await send_group_page(bot, call.message.chat.id, user_id, page)


async def with_telethon_client(session_name: str, coro):
    """
    Safely use Telethon client within a coroutine.
    """
    client = TelegramClient(session_name, API_ID, API_HASH)
    await client.connect()
    try:
        return await coro(client)
    finally:
        await client.disconnect()


async def send_group_page(bot: Bot, chat_id: int, user_id: int, page: int) -> None:
    """
    Send a paginated list of groups and channels.
    """
    # Check if user data exists
    if user_id not in pending_logins or "groups" not in pending_logins[user_id]:
        await bot.send_message(chat_id, NO_GROUPS_FOUND_MESSAGE)
        return

    group_list = pending_logins[user_id]["groups"]
    total_pages = (len(group_list) + GROUPS_PER_PAGE - 1) // GROUPS_PER_PAGE

    # Validate page
    if page < 0 or page >= total_pages:
        await bot.send_message(chat_id, INVALID_PAGE_NUMBER_MESSAGE)
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

    # Add "Search" and "Return" buttons
    markup.row(
        InlineKeyboardButton("Search", callback_data="search_groups"),
        InlineKeyboardButton("Return", callback_data="return_to_menu"),
    )

    # Pagination buttons
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"navigate:{page - 1}"))
    pagination_buttons.append(InlineKeyboardButton(f"Page {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"navigate:{page + 1}"))
    markup.row(*pagination_buttons)

    # Send the paginated message
    await bot.send_message(chat_id, GROUP_PAGE_INSTRUCTION, reply_markup=markup)


def register_group_handlers(dp: Dispatcher, bot: Bot):
    """
    Register group-related command handlers with the dispatcher.
    """
    dp.register_message_handler(lambda msg: list_groups_command(msg, bot), commands=["list_groups"])
    dp.register_callback_query_handler(lambda call: toggle_group(call, bot), lambda call: call.data.startswith("toggle_group"))
    dp.register_callback_query_handler(lambda call: navigate_page(call, bot), lambda call: call.data.startswith("navigate"))