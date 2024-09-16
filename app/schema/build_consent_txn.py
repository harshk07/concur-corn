from fastapi import HTTPException
from bson import ObjectId
# from app.config.private import *
from app.config.private import *
from web3 import Web3
import json, requests
import datetime


def build_consent_transaction():
    try:
        # Connect to Ethereum network (Sepolia, Goerli, or local)
        w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:22000'))

        # Fetch all documents in consent_collection where is_txn_build is False
        pending_consents = consent_collection.find({"is_txn_build": False})

        count = 0
        for pending_consent in pending_consents:
            count += 1
            print(pending_consent)

            consent_id = pending_consent["_id"]
            dp_id = pending_consent["dp_id"]
            dp_email_hash = pending_consent["dp_email_hash"]
            dp_mobile_hash = pending_consent["dp_mobile_hash"]

            print(f"Processing consent: {consent_id}, dp_id: {dp_id}")

            # Fetch collection point data based on org_id and cp_id from pending consent
            collection_point_data = collection_points.find_one({"org_id": pending_consent["org_id"], "cp_id": pending_consent["cp_id"]})
            if not collection_point_data:
                raise HTTPException(status_code=500, detail=f"Collection point data not found for org_id {pending_consent['org_id']} and cp_id {pending_consent['cp_id']}")

            # Load the contract ABI and address
            contract_address = Web3.to_checksum_address(collection_point_data["contract_address"])
            with open('app/routes/SaveConsent2.json', 'r') as abi_file:
                contract_abi = json.load(abi_file)

            contract = w3.eth.contract(address=contract_address, abi=contract_abi)

            # Call the /get-user-wallet-address API to get the wallet address
            wallet_address_url = "http://127.0.0.1:7000/get-user-wallet-address"
            wallet_response = requests.get(wallet_address_url, params={"dp_id": dp_id, "dp_email_hash": dp_email_hash or None, "dp_mobile_hash": dp_mobile_hash or None})

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
                "is_signed": False,
                "is_published_to_blockchain": False
            }
            build_txn_id = build_transaction_collection.insert_one(build_txn_data).inserted_id

            # Fetch the data from `build_transaction_collection`
            build_txn = build_transaction_collection.find_one({"_id": build_txn_id})

            # Prepare the data to send to /send-build-transaction API
            send_build_txn_data = {
                "dp_id": build_txn["dp_id"],
                "transaction": build_txn["transaction"],
                "created_at": build_txn["created_at"].isoformat(),  # Convert datetime to ISO format string
                "is_signed": build_txn["is_signed"]
            }

            # Call the /send-build-transaction API to post the build transaction data to custody
            send_build_txn_url = "http://127.0.0.1:7000/send-build-transaction"
            send_build_txn_response = requests.post(send_build_txn_url, json=send_build_txn_data)

            # Check if the request was successful
            if send_build_txn_response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Error sending build transaction for consent ID {consent_id}: {send_build_txn_response.json()}")

            # Get the response data containing signed_txn_id and signed_transaction
            response_data = send_build_txn_response.json()
            signed_txn_id = response_data.get("signed_txn_id")
            signed_transaction = response_data.get("signed_transaction")

            if signed_txn_id and signed_transaction:
                # Update the `is_signed`, `signed_txn_id`, and `signed_transaction` fields in `build_transaction_collection`
                build_transaction_collection.update_one(
                    {"_id": build_txn_id},
                    {"$set": {
                        "is_signed": True,
                        "signed_txn_id": signed_txn_id,
                        "signed_transaction": signed_transaction
                    }}
                )
                print(f"Transaction signed for consent ID {consent_id}: Signed TXN ID {signed_txn_id}")
            else:
                print(f"Error: Missing signed_txn_id or signed_transaction for consent ID {consent_id}")

            # Update the `is_txn_build` flag in the `consent_collection`
            consent_collection.update_one(
                {"_id": consent_id},
                {"$set": {"is_txn_build": True}}
            )

        if count == 0:
            print("No pending consent transactions found")

        return {"status": "success", "message": "Transactions built, signed, and sent for all pending consents"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

