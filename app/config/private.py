from pymongo import MongoClient

# MongoDB connection URI
uri = "mongodb://gewgawrav:catax1234@concur.cumulate.live/"

# Create a new client and connect to the server
client = MongoClient(uri)

# Access the specific database
db = client["consent_foundation"]

# Access the specific collection
collection_points = db["collection_points"]
consent_collection = db["consent_collection"]
build_transaction_collection = db["build_transaction_collection"]
transaction_receipts_collection = db["transaction_receipts_collection"]
user_txn_collection = db['blockchain_user_transaction_collection']
chaukidar_collection = db['chaukidar_collection']