from MongoDB.connect_database import db

session = {
    "server_ID": "",
    "is_Playing": False,
    "is_Paused": False,
    # current song
    "current_track": None,
    # person who queued current song
    "current_person": None,
    "music_queue": [],
    # settings for optimal audio
    "vc": None
}

# test post function
# def post():
#     collection = db.get_collection("music_sessions")
#     print(f"This is the collection: {collection}")
#     post_id = collection.insert_one(session).inserted_id
#     print("Inserted document ID:", post_id)
