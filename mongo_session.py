from telethon.sessions import MemorySession

class MongoSession(MemorySession):
    def __init__(self, user_id, db):
        super().__init__()
        self.user_id = user_id
        self.collection = db["telethon_sessions"]
        self.load()

    def load(self):
        session_data = self.collection.find_one({"_id": self.user_id})
        if session_data:
            self.unpack(session_data["session"])  # Load the session data

    def save(self):
        session_data = {
            "_id": self.user_id,
            "session": self.save_to_string()  # Save the session as a string
        }
        self.collection.update_one({"_id": self.user_id}, {"$set": session_data}, upsert=True)
