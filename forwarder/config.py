from .db import db
import logging

# Load MongoDB collections
users_collection = db["users"]
group_configs_collection = db["group_configs"]

def get_user_settings(user_id, fields=None):
    """
    Fetch user-specific settings saved by the admin bot.

    Args:
        user_id (str): The ID of the user to fetch settings for.
        fields (list, optional): Specific fields to fetch for optimization. Defaults to None.

    Returns:
        dict: The user's settings.

    Raises:
        ValueError: If no configuration is found for the user.
    """
    try:
        query = {"_id": user_id}
        projection = {field: 1 for field in fields} if fields else None
        user = users_collection.find_one(query, projection)

        if not user:
            raise ValueError(f"No configuration found for user ID: {user_id}")
        
        logging.info(f"User settings fetched successfully for user ID: {user_id}")
        return user
    except Exception as e:
        logging.error(f"Error fetching user settings for user ID: {user_id} - {e}")
        raise
