from pymongo import MongoClient
from admin.config import MONGO_URI

# Connect to MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['kaoru']

# Collections
users_collection = db['users']
sessions_collection = db['sessions']
group_configs_collection = db['group_configs']

def get_or_create_user(user_id: int, username: str = None) -> dict:
    """
    Retrieve an existing user from the database or create a new one if not found.

    Args:
        user_id (int): The Telegram user ID.
        username (str): Optional username to set or update.

    Returns:
        dict: User document from MongoDB.
    """
    user = users_collection.find_one({"_id": user_id})
    if not user:
        user = {
            "_id": user_id,
            "username": username,
            "source_group_ids": [],
            "destination_group_id": None,
            "trading_bot_id": None,
        }
        users_collection.insert_one(user)
    elif username and user.get("username") != username:
        users_collection.update_one(
            {"_id": user_id}, {"$set": {"username": username}}
        )
        user["username"] = username
    return user

def update_user(user_id: int, updates: dict):
    """
    Update a user's information in the database.

    Args:
        user_id (int): The Telegram user ID.
        updates (dict): Fields to update.
    """
    users_collection.update_one({"_id": user_id}, {"$set": updates})

def delete_user_session(user_id: int):
    """
    Remove a user's session data from the database.

    Args:
        user_id (int): The Telegram user ID.
    """
    users_collection.update_one({"_id": user_id}, {"$unset": {"session_name": ""}})
    sessions_collection.delete_one({"user_id": user_id})

def save_session(user_id: int, session_data: str):
    """
    Save a Telethon session string to the database.

    Args:
        user_id (int): The Telegram user ID.
        session_data (str): Serialized session data.
    """
    sessions_collection.update_one(
        {"user_id": user_id},
        {"$set": {"session_data": session_data}},
        upsert=True
    )

def load_session(user_id: int) -> str:
    """
    Load a Telethon session string from the database.

    Args:
        user_id (int): The Telegram user ID.

    Returns:
        str: Serialized session data or None if not found.
    """
    session_entry = sessions_collection.find_one({"user_id": user_id})
    return session_entry["session_data"] if session_entry else None
