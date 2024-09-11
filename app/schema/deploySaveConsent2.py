import json
from web3 import Web3
from pymongo import ReturnDocument
from app.config.private import collection_points  # Assuming MongoDB collection is configured here

# Initialize Web3 connection
host = "http://127.0.0.1:22000"
address = Web3.to_checksum_address("0x2cace882f2ab92994d534b1a4b300ef22a490263")
w3 = Web3(Web3.HTTPProvider(host))

# Load contract ABI and bytecode
contract_json_path = "app/schema/SaveConsent.json"
with open(contract_json_path, 'r') as file:
    contract_json = json.load(file)
contract_abi = contract_json['abi']
contract_bytecode = contract_json['bytecode']

# Function to create and deploy the contract
def create_contract(w3, contract_abi, contract_bytecode, from_address):
    contract = w3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
    tx = contract.constructor().build_transaction({
        'from': from_address,
        'gas': 1500000,
        'gasPrice': w3.to_wei('0', 'gwei'),
        'nonce': w3.eth.get_transaction_count(from_address),
    })
    
    private_key = "0x10302650bba084cb367619521b9879af3f2b9bba4533a6cb984e94764371c8a3"
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    return w3.to_hex(tx_hash), tx_receipt.contractAddress

# Function to check and deploy contracts based on blockchain_status
def check_cp():
    # Try to find one collection point that has `blockchain_status: "not_deployed"`
    cp = collection_points.find_one_and_update(
        {
            "blockchain_status": "not deployed",  # Marked as not deployed
        },
        {"$set": {"blockchain_status": "deploying"}},  # Lock the document by setting the status to 'deploying'
        return_document=ReturnDocument.AFTER
    )
    
    if cp:
        try:
            # Deploy the smart contract and get the transaction hash and contract address
            tx_hash, contract_address = create_contract(
                w3, contract_abi, contract_bytecode, address
            )

            # Update the document in MongoDB with txn_hash, contract_address, and set blockchain_status to 'deployed'
            collection_points.update_one(
                {"_id": cp["_id"]},
                {
                    "$set": {
                        "blockchain_status": "deployed",  # Mark as deployed
                        "txn_hash": tx_hash,
                        "contract_address": contract_address,
                    }
                }
            )
            print(f"Contract deployed for collection point: {cp['_id']}")

        except Exception as e:
            # If there is an error, set blockchain_status back to 'not_deployed'
            collection_points.update_one(
                {"_id": cp["_id"]},
                {"$set": {"blockchain_status": "not deployed"}}
            )
            print(f"Error deploying contract for collection point {cp['_id']}: {e}")
    else:
        print("No collection points with 'not deployed' status found.")
