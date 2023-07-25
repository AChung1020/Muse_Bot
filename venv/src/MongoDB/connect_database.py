import pymongo
from dotenv import load_dotenv

load_dotenv()


def get_mongo_client():
    client = pymongo.MongoClient("MONGO_URI")

    db = client.Discord_Music_db
    print("Current database name:", db)
