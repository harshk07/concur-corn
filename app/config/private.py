from pymongo import MongoClient

# MongoDB connection URI
uri = "mongodb://gewgawrav:catax1234@concur.cumulate.live/"

# Create a new client and connect to the server
client = MongoClient(uri)

# Access the specific database
db = client["consent_foundation"]

# Access the specific collection
collection_points = db["collection_points"]