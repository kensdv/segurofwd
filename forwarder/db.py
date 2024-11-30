from pymongo import MongoClient

def connect_to_mongo(uri):
    """
    Connect to MongoDB and return the database and collections.
    """
    client = MongoClient(uri)
    db = client['kaoru']
    users_collection = db['users']
    group_configs_collection = db['group_configs']
    return db, users_collection, group_configs_collection
