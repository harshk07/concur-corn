from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from web3 import Web3
import json
from web3.exceptions import ContractLogicError, TransactionNotFound
contractInteractRoute = APIRouter()

# Connect to Ethereum network (Sepolia, Goerli, or local)
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))

# Load the contract ABI and address
contract_address = Web3.to_checksum_address('0x73e05866b28e20225ef1e29355bb135229c2f974')
with open('app/routes/SaveConsent2.json', 'r') as abi_file:
    contract_abi = json.load(abi_file)

contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# Models to reflect the structure of the smart contract
class ConsentEntry(BaseModel):
    purpose_id: str
    consent_status: bool
    purpose_retention: int
    purpose_expiry: int

class ConsentScope(BaseModel):
    dataElement: str
    consents: list[ConsentEntry]

class ConsentInput(BaseModel):
    dp_id: str
    df_id: str
    cp_id: str
    consent_scopes: list[ConsentScope]

@contractInteractRoute.post("/storeConsent")
async def store_consent(input: ConsentInput):
    try:
        account = '0xD3Efcb75b86A50eaA849B87c5fbC7040f03De44F'
        private_key = '0xb2b41ff11481cebad435be54de43e40f9c5450872079d93318e780558075d77f'

        # Prepare data for the transaction
        data_elements = [scope.dataElement for scope in input.consent_scopes]
        purposes = [[entry.purpose_id for entry in scope.consents] for scope in input.consent_scopes]
        consent_statuses = [[entry.consent_status for entry in scope.consents] for scope in input.consent_scopes]
        # consent_statuses = [[1]]
        retention_periods = [[entry.purpose_retention for entry in scope.consents] for scope in input.consent_scopes]
        expiry_periods = [[entry.purpose_expiry for entry in scope.consents] for scope in input.consent_scopes]

        # Build the transaction object
        txn = contract.functions.storeConsent(
            input.dp_id,
            input.df_id,
            input.cp_id,
            data_elements,
            purposes,
            consent_statuses,
            retention_periods,
            expiry_periods
        ).build_transaction({
            'from': account,
            'nonce': w3.eth.get_transaction_count(account),
            'gas': 4000000,  # Estimated gas, you can try dynamically estimating it too
            'gasPrice': w3.to_wei('50', 'gwei')
        })
        print(txn)

        # Sign the transaction
        signed_txn = w3.eth.account.sign_transaction(txn, private_key=private_key)

        # Send the transaction
        txn_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

        # Wait for the receipt
        txn_receipt = w3.eth.wait_for_transaction_receipt(txn_hash)

        # Return success and transaction hash
        return {"status": "success", "txn_hash": txn_hash.hex()}

    except ContractLogicError as e:
        # Extract the revert reason from the error
        revert_reason = str(e).split("revert")[1].strip() if "revert" in str(e) else str(e)
        raise HTTPException(status_code=500, detail=f"Transaction reverted: {revert_reason}")

    except TransactionNotFound as e:
        raise HTTPException(status_code=500, detail="Transaction not found on the blockchain. It might have failed.")

    except ValueError as e:
        # Handle other value errors (like insufficient gas, nonce issues, etc.)
        error_message = json.loads(e.args[0]) if e.args else str(e)
        raise HTTPException(status_code=500, detail=f"Transaction error: {error_message}")

    except Exception as e:
        # General error handler for any unforeseen issues
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")




@contractInteractRoute.get("/getConsent/{user_address}")
async def get_consent(user_address: str):
    try:
        # Call the getConsent function from the contract
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
