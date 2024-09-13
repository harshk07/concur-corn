from fastapi import HTTPException
from bson import ObjectId
# from app.config.private import *
from app.config.private import *
from web3 import Web3
import json, requests
import datetime
# Connect to Ethereum network (Sepolia, Goerli, or local)
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:22000'))

# Load the contract ABI and address
contract_address = Web3.to_checksum_address('0x386a79c234eb6c1e4e35741346430ede3b46e50d')
with open('app/routes/SaveConsent2.json', 'r') as abi_file:
    contract_abi = json.load(abi_file)

contract = w3.eth.contract(address=contract_address, abi=contract_abi)

def build_consent_transaction():
    try:
        # Fetch all documents in consent_collection where is_txn_build is False
        pending_consents = consent_collection.find({"is_txn_build": False})

        count = 0
        for pending_consent in pending_consents:
            count += 1
            print(pending_consent)

            consent_id = pending_consent["_id"]
            dp_id = pending_consent["dp_id"]

            print(f"Processing consent: {consent_id}, dp_id: {dp_id}")

            # Call the /get-user-wallet-address API to get the wallet address
            wallet_address_url = "http://127.0.0.1:7000/get-user-wallet-address"
            wallet_response = requests.get(wallet_address_url, params={"dp_id": dp_id})

            # Check if the request was successful
            if wallet_response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Error fetching wallet address for consent ID {consent_id}: {wallet_response.json()}")

            wallet_address = wallet_response.json().get("wallet_address")
            if not wallet_address:
                raise HTTPException(status_code=500, detail=f"No wallet address returned for dp_id {dp_id}")

            # Extract data from the pending consent
            data_elements = [scope["dataElement"] for scope in pending_consent["consent_scopes"]]
            purposes = [[entry["purpose_id"] for entry in scope["consents"]] for scope in pending_consent["consent_scopes"]]
            consent_statuses = [[entry["consent_status"] for entry in scope["consents"]] for scope in pending_consent["consent_scopes"]]
            retention_periods = [[entry["purpose_retention"] for entry in scope["consents"]] for scope in pending_consent["consent_scopes"]]
            expiry_periods = [[entry["purpose_expiry"] for entry in scope["consents"]] for scope in pending_consent["consent_scopes"]]

            # Build the transaction using the fetched wallet address (without signing it)
            txn = contract.functions.storeConsent(
                pending_consent["dp_id"],
                pending_consent["df_id"],
                pending_consent["cp_id"],
                data_elements,
                purposes,
                consent_statuses,
                retention_periods,
                expiry_periods
            ).build_transaction({
                'from': wallet_address,  # Use the retrieved wallet address
                'nonce': w3.eth.get_transaction_count(wallet_address),
                'gas': 4000000,
                'gasPrice': w3.to_wei('0', 'gwei')
            })

            # Store the built transaction in the `build_transaction_collection`
            build_txn_data = {
                "consent_id": str(consent_id),
                "dp_id": dp_id,
                "transaction": txn,
                "created_at": datetime.datetime.utcnow(),
                "is_signed": False
            }
            build_txn_id = build_transaction_collection.insert_one(build_txn_data).inserted_id

            # Update the `is_txn_build` flag in the `consent_collection`
            consent_collection.update_one(
                {"_id": consent_id},
                {"$set": {"is_txn_build": True}}
            )

            print(f"Transaction built for consent ID {consent_id}: Build TXN ID {build_txn_id}")

        if count == 0:
            print("No pending consent transactions found")
            # raise HTTPException(status_code=404, detail="No pending consent transactions found")

        return {"status": "success", "message": "Transactions built for all pending consents"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
