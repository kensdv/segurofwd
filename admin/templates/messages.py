# Welcome message for /start command
WELCOME_MESSAGE = (
    "👋 Welcome to **Seguro Fwd Bot – Test Edition!**\n\n"
    "⚙️ **Features:**\n"
    "- 🔐 Secure login process\n"
    "- 🔍 Seamless tracking of groups and listening for CA\n"
    "- 💼 24/7 forwarding for CA from selected group/channel\n"
    "- ⏳ Forwards CA to your trading bot for Autobuys\n"
    "- 👩‍💻 Fully user control based\n\n"
    "📢 **Stay Updated:**\n"
    "DM @kensgx for essential updates/enquiries.\n\n"
    "Use /help to see all available commands."
)

# Help message for /help command
HELP_MESSAGE = (
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

# Message for invalid OTP format
INVALID_OTP_FORMAT_MESSAGE = (
    "Invalid format! Please prepend 'XX' to the OTP and send it (e.g., 'XX12345')."
)

OTP_SENT_MESSAGE = "Your OTP has been sent."

LOGIN_REQUEST_MESSAGE = "Your login request has been received."
# Ensure other constants or imports are defined correctly

INVALID_OTP_MESSAGE = "The OTP you entered is invalid."

INVALID_PHONE_NUMBER_MESSAGE = "The phone number you entered is invalid."

# Message for login success
LOGIN_SUCCESS_MESSAGE = "✅ Login successful! You can now use the bot."

# Message for login success with 2FA
LOGIN_SUCCESS_2FA_MESSAGE = "✅ Login successful with 2FA! You can now use the bot."

# Message for login failure
LOGIN_FAILURE_MESSAGE = "❌ Login failed. Please try again."

# Message for unauthorized session
SESSION_UNAUTHORIZED_MESSAGE = "⚠️ Your session is not authorized. Please log in again using /login."

# Message for no groups found
NO_GROUPS_FOUND_MESSAGE = "⚠️ No groups found. Please use /list_groups to refresh."

# Message for logout success
LOGOUT_SUCCESS_MESSAGE = "✅ You have been logged out successfully."

# Message for logout failure
LOGOUT_FAILURE_MESSAGE = "❌ Logout failed. Please try again."

# Message for invalid input
INVALID_INPUT_MESSAGE = "❌ Invalid input. Please check the command usage."

# Message for command usage
COMMAND_USAGE_MESSAGE = "Usage: /set_destination <group_id or @group_username>"

PASSWORD_REQUIRED_MESSAGE = "Password is required to continue."


# Message when the trading bot is successfully set
TRADING_BOT_SET_MESSAGE = "✅ Trading bot set to: {bot_name} (ID: {bot_id})"

# Message when the trading bot setup fails
TRADING_BOT_SETUP_ERROR_MESSAGE = "❌ Error setting trading bot: {error}"

# Pagination navigation buttons
NEXT_PAGE_BUTTON = "Next ➡️"
PREVIOUS_PAGE_BUTTON = "⬅️ Back"
PAGE_INFO = "Page {current}/{total}"

# Confirmation messages
DESTINATION_GROUP_SET_MESSAGE = "✅ Destination group set to ID: {group_id}"
NOTIFIER_GROUP_SET_MESSAGE = "✅ Notifier for source {source_id} set to: {notifier_name}"
RESET_CONFIG_MESSAGE = "✅ Configuration has been reset."
