from fastapi import HTTPException
from bson import ObjectId
from web3 import Web3
from app.config.private import *
import json, datetime

# Connect to Ethereum network (Sepolia, Goerli, or local)
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:22000'))

# Load the contract ABI and address
contract_address = Web3.to_checksum_address('0x386a79c234eb6c1e4e35741346430ede3b46e50d')
with open('app/routes/SaveConsent2.json', 'r') as abi_file:
    contract_abi = json.load(abi_file)

contract = w3.eth.contract(address=contract_address, abi=contract_abi)

from bson import ObjectId

def push_signed_transactions_to_blockchain():
    try:
        # Fetch all documents from build_transaction_collection where is_signed = True
        signed_transactions = build_transaction_collection.find({"is_signed": True, "is_published_in_blockchain": False})
        
        for signed_txn_data in signed_transactions:
            try:
                # Extract the signed transaction data
                signed_txn = signed_txn_data["signed_transaction"]

                # Send the signed transaction to the blockchain
                txn_hash = w3.eth.send_raw_transaction(signed_txn)

                # Wait for the transaction receipt
                txn_receipt = w3.eth.wait_for_transaction_receipt(txn_hash)

                # Store the transaction receipt in the database (transaction_receipts_collection)
                txn_receipt_data = {
                    "transaction_hash": txn_receipt.transactionHash.hex(),
                    "block_hash": txn_receipt.blockHash.hex(),
                    "block_number": txn_receipt.blockNumber,
                    "gas_used": txn_receipt.gasUsed,
                    "status": txn_receipt.status,  # Status 1 means success
                    "logs": txn_receipt.logs,
                    "created_at": datetime.datetime.utcnow()
                }
                txn_receipt_id = transaction_receipts_collection.insert_one(txn_receipt_data).inserted_id

                # Update the build_transaction_collection with the transaction receipt ID
                build_transaction_collection.update_one(
                    {"_id": ObjectId(signed_txn_data["_id"])},
                    {"$set": {
                        "is_published_to_blockchain": True,
                        "txn_hash": txn_receipt.transactionHash.hex(),
                        "block_number": txn_receipt.blockNumber,
                        "txn_receipt_id": str(txn_receipt_id)
                    }}
                )

                print(f"Transaction pushed for signed_txn_id {signed_txn_data['_id']}: Hash {txn_receipt.transactionHash.hex()}")

            except Exception as e:
                print(f"Error occurred while pushing transaction for signed_txn_id {signed_txn_data['_id']}: {str(e)}")

        return {"status": "success", "message": "All signed transactions have been pushed to the blockchain"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
