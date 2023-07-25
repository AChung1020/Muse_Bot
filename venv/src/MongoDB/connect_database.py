from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os

current_dir = os.path.dirname(os.path.dirname(__file__))
dotenv_path = os.path.join(current_dir, ".env")

result = load_dotenv(dotenv_path)

db = None


def get_mongo_client():
    global db

    if db is not None:
        return
    client = MongoClient(os.getenv("MONGO_URI"), server_api=ServerApi('1'))

    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")

    db = client.Discord_Music_db


