from web3 import Web3
from datetime import datetime
# from app.config.private import consent_collection, collection_points, user_txn_collection, chaukidar_collection
import datetime
import requests
from bson import ObjectId
# from config.private import chaukidar_collection,collection_points,user_txn_collection
from app.config.private import *
# from config import private
from pymongo import MongoClient

# # MongoDB connection URI
# uri = "mongodb://gewgawrav:catax1234@concur.cumulate.live/"

# # Create a new client and connect to the server
# client = MongoClient(uri)

# # Access the specific database
# db = client["consent_foundation"]

# # Access the specific collection
# collection_points = db["collection_points"]
# consent_collection = db["consent_collection"]
# build_transaction_collection = db["build_transaction_collection"]
# transaction_receipts_collection = db["transaction_receipts_collection"]
# user_txn_collection = db['blockchain_user_transaction_collection']
# chaukidar_collection = db['chaukidar_collection']

# Connect to the blockchain RPC URL
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:22000'))

# # Connect to MongoDB
# mongo_client = MongoClient('mongodb://localhost:27017')
# db = mongo_client['your_database_name']

def chaukidar():
    # Get the latest block
    latest_block = w3.eth.get_block('latest')['number']

    # Get the last block read from chaukidar_collection
    last_block_data = chaukidar_collection.find_one({}, sort=[('last_block_read', -1)])
    last_block = last_block_data['last_block_read'] if last_block_data else 0

    # Start time for the current chaukidar
    start_time = datetime.now()

    # Iterate through new blocks
    for block_number in range(last_block + 1, latest_block + 1):
        block = w3.eth.get_block(block_number, full_transactions=True)

        for txn in block['transactions']:
            txn_to = txn['to']
            txn_from = txn['from']

            # Check if 'to' address matches any contract_address in collection_points
            contract = collection_points.find_one({'contract_address': txn_to})
            if contract:
                # Check if the user's wallet address exists in the transaction collection
                user_doc = user_txn_collection.find_one({'dp_walletAddress': txn_from})

                if user_doc:
                    # Update the transactions array with the new transaction
                    user_txn_collection.update_one(
                        {'dp_walletAddress': txn_from},
                        {'$push': {'transactions': txn['hash'].hex()}}
                    )
                else:
                    # Create a new document for the new user
                    user_txn_collection.insert_one({
                        'dp_walletAddress': txn_from,
                        'transactions': [txn['hash'].hex()]
                    })

        # Update the last block read in chaukidar_collection
        chaukidar_collection.update_one(
            {'_id': last_block_data['_id']} if last_block_data else {},
            {
                '$set': {
                    'last_block_read': block_number,
                    'end_time': datetime.now()
                },
                '$setOnInsert': {
                    'start_time': start_time
                }
            },
            upsert=True
        )

chaukidar()

