from Database.connect_database import db


def music_sessions():
    return db["music_sessions"]


def find_document(server_id):
    collection = music_sessions()
    document = collection.find_one({"_id": server_id})
    return document


# data for new song inputted
def add_music_queue(m_url, title, queuer, channel):
    song = {"source": m_url,
            "title": title,
            "queuer": queuer,
            "channel": channel
            }
    return song
