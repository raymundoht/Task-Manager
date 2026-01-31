from pymongo import MongoClient

uri = "mongodb+srv://rayherrera313:Ray12345@cluster0.ejne3zv.mongodb.net/proyectoclas?retryWrites=true&w=majority"

client = MongoClient(uri, serverSelectionTimeoutMS=5000)
db = client["proyectoclas"]

print(db.command("ping"))
print(db.list_collection_names())
