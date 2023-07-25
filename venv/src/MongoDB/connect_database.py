import pymongo
from dotenv import load_dotenv

load_dotenv()

db = None


def get_mongo_client():
    global db

    if db is not None:
        return
    client = pymongo.MongoClient("MONGO_URI")

    db = client.Discord_Music_db
    print("Current database name:", db)
    return db


print(db)
