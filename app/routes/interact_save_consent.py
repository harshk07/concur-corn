from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from web3 import Web3
import json
from web3.exceptions import ContractLogicError, TransactionNotFound
from app.config.private import consent_collection
import datetime
from app.config.private import *
import requests
from bson import ObjectId

contractInteractRoute = APIRouter()

# Connect to Ethereum network (Sepolia, Goerli, or local)
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:22000'))

# Load the contract ABI and address
contract_address = Web3.to_checksum_address('0xC1C1F0fB406e0b4126e8D21b81C98B2C4C582f79')
with open('app/routes/SaveConsent2.json', 'r') as abi_file:
    contract_abi = json.load(abi_file)

contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# Models to reflect the structure of the smart contract
class ConsentEntry(BaseModel):
    purpose_id: str
    consent_status: bool = False
    purpose_retention: int
    purpose_expiry: int

class ConsentScope(BaseModel):
    dataElement: str
    consents: list[ConsentEntry]

class ConsentInput(BaseModel):
    dp_id: str
    dp_email_hash: str = None
    dp_mobile_hash: str = None
    org_id: str
    df_id: str
    cp_id: str
    consent_scopes: list[ConsentScope]

@contractInteractRoute.post("/store-consent", tags = ["Consent Management"])
async def store_consent(input: ConsentInput):
    try:
        # Prepare data for MongoDB
        consent_data = {
            "dp_id": input.dp_id,
            "dp_email_hash": input.dp_email_hash,
            "dp_mobile_hash": input.dp_mobile_hash,
            "org_id": input.org_id,
            "df_id": input.df_id,
            "cp_id": input.cp_id,
            "consent_scopes": [scope.dict() for scope in input.consent_scopes],
            "is_txn_build": False,
            "created_at": datetime.datetime.utcnow()
        }

        # Insert the data into MongoDB
        inserted_id = consent_collection.insert_one(consent_data).inserted_id

        # Return the inserted document ID
        return {"status": "success", "confirmation_id": str(inserted_id)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# @contractInteractRoute.post("/storeConsent")
# async def store_consent(input: ConsentInput):
#     try:
#         account = '0xD3Efcb75b86A50eaA849B87c5fbC7040f03De44F'
#         private_key = '0xb2b41ff11481cebad435be54de43e40f9c5450872079d93318e780558075d77f'

#         # Prepare data for the transaction
#         data_elements = [scope.dataElement for scope in input.consent_scopes]
#         purposes = [[entry.purpose_id for entry in scope.consents] for scope in input.consent_scopes]
#         consent_statuses = [[entry.consent_status for entry in scope.consents] for scope in input.consent_scopes]
#         retention_periods = [[entry.purpose_retention for entry in scope.consents] for scope in input.consent_scopes]
#         expiry_periods = [[entry.purpose_expiry for entry in scope.consents] for scope in input.consent_scopes]

#         # Build the transaction object
#         txn = contract.functions.storeConsent(
#             input.dp_id,
#             input.df_id,
#             input.cp_id,
#             data_elements,
#             purposes,
#             consent_statuses,
#             retention_periods,
#             expiry_periods
#         ).build_transaction({
#             'from': account,
#             'nonce': w3.eth.get_transaction_count(account),
#             'gas': 4000000,  # Estimated gas, you can try dynamically estimating it too
#             'gasPrice': w3.to_wei('50', 'gwei')
#         })
#         print(txn)

#         # Sign the transaction
#         signed_txn = w3.eth.account.sign_transaction(txn, private_key=private_key)

#         # Send the transaction
#         txn_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

#         # Wait for the receipt
#         txn_receipt = w3.eth.wait_for_transaction_receipt(txn_hash)

#         # Return success and transaction hash
#         return {"status": "success", "txn_hash": txn_hash.hex()}

#     except ContractLogicError as e:
#         # Extract the revert reason from the error
#         revert_reason = str(e).split("revert")[1].strip() if "revert" in str(e) else str(e)
#         raise HTTPException(status_code=500, detail=f"Transaction reverted: {revert_reason}")

#     except TransactionNotFound as e:
#         raise HTTPException(status_code=500, detail="Transaction not found on the blockchain. It might have failed.")

#     except ValueError as e:
#         # Handle other value errors (like insufficient gas, nonce issues, etc.)
#         error_message = json.loads(e.args[0]) if e.args else str(e)
#         raise HTTPException(status_code=500, detail=f"Transaction error: {error_message}")

#     except Exception as e:
#         # General error handler for any unforeseen issues
#         raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@contractInteractRoute.post("/build-consent-transaction", tags =["Consent Foundation APIs"])
async def build_consent_transaction(consent_id: str):
    try:
        # Convert consent_id to ObjectId
        try:
            consent_object_id = ObjectId(consent_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid consent ID format")

        # Find the consent entry by MongoDB _id and check if the transaction is not built
        pending_consent = consent_collection.find_one({"_id": consent_object_id, "is_txn_build": False})
        if not pending_consent:
            raise HTTPException(status_code=404, detail="No pending consent transaction found for the given ID")

        dp_id = pending_consent["dp_id"]

        # Call the /get-user-wallet-address API to get the wallet address
        wallet_address_url = "http://127.0.0.1:7000/get-user-wallet-address"
        wallet_response = requests.get(wallet_address_url, params={"dp_id": dp_id})
        
        # Check if the request was successful
        if wallet_response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Error fetching wallet address: {wallet_response.json()}")

        wallet_address = wallet_response.json().get("wallet_address")
        if not wallet_address:
            raise HTTPException(status_code=500, detail="No wallet address returned for the given dp_id")

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
            "consent_id": str(pending_consent["_id"]),
            "dp_id": dp_id,
            "transaction": txn,
            "created_at": datetime.datetime.utcnow(),
            "is_signed": False
        }
        build_txn_id = build_transaction_collection.insert_one(build_txn_data).inserted_id

        # Update the `is_txn_build` flag in the `consent_collection`
        consent_collection.update_one(
            {"_id": pending_consent["_id"]},
            {"$set": {"is_txn_build": True}}
        )

        return {"status": "success", "build_txn_id": str(build_txn_id)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@contractInteractRoute.get("/get-consent/{user_address}", tags = ["Consent Management"])
async def get_consent(user_address: str, contract_address: str):
    try:
        # Call the getConsent function from the contract
        user_address = Web3.to_checksum_address(user_address)

        # Load the contract ABI and address
        contract_address = Web3.to_checksum_address(contract_address)
        with open('app/routes/SaveConsent2.json', 'r') as abi_file:
            contract_abi = json.load(abi_file)

        contract = w3.eth.contract(address=contract_address, abi=contract_abi)

        consent_data = contract.functions.getConsent(user_address).call()

        # Process the retrieved data
        consent_scopes = []
        for scope in consent_data[3]:
            consents = []
            for entry in scope[1]:
                consents.append({
                    "purpose_id": entry[0],
                    "consent_status": entry[1],
                    "purpose_retention": entry[2],
                    "purpose_expiry": entry[3]
                })
            consent_scopes.append({
                "dataElement": scope[0],
                "consents": consents
            })

        return {
            "dp_id": consent_data[0],
            "df_id": consent_data[1],
            "cp_id": consent_data[2],
            "consent_scope": consent_scopes
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
class SignedTransactionData(BaseModel):
    signed_transaction: str

@contractInteractRoute.post("/push-to-blockchain", tags =["Consent Foundation APIs"])
async def push_to_blockchain(signed_txn_data: SignedTransactionData):
    try:
        # Decode the signed transaction from the provided hex string
        signed_txn = signed_txn_data.signed_transaction

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

        return {
            "status": "success",
            "txn_hash": txn_receipt.transactionHash.hex(),
            "block_number": txn_receipt.blockNumber,
            "txn_receipt_id": str(txn_receipt_id)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while pushing the transaction: {str(e)}")
