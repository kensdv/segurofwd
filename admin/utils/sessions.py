from telethon.sessions import StringSession
from admin.utils.mongodb import save_session, load_session

class MongoSession(StringSession):
    """
    A custom Telethon session class that stores session data in MongoDB.
    """
    def __init__(self, user_id: int, db):
        """
        Initialize the session with a user ID and database reference.

        Args:
            user_id (int): The Telegram user ID.
            db: The MongoDB database instance.
        """
        super().__init__()
        self.user_id = user_id
        self.db = db
        self.load()

    def save(self):
        """
        Serialize and save the session data to MongoDB.
        """
        session_data = self.save_to_string()
        save_session(self.user_id, session_data)

    def load(self):
        """
        Load the session data from MongoDB, if it exists.
        """
        session_data = load_session(self.user_id)
        if session_data:
            self.load_from_string(session_data)

    def save_to_string(self):
        """
        Serialize the session data to a string format.

        Returns:
            str: Serialized session data.
        """
        return super().save()

    def load_from_string(self, session_str):
        """
        Load session data from a serialized string.

        Args:
            session_str (str): Serialized session data.
        """
        super().load(session_str)
