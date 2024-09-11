import json
from web3 import Web3


# Define the host and account address (replace with your own account)
host = "http://127.0.0.1:22000"
address = Web3.to_checksum_address("0x2cace882f2ab92994d534b1a4b300ef22a490263")

# Read the contract's ABI and Bytecode from the JSON file
contract_json_path = "./SaveConsent.json"
with open(contract_json_path, 'r') as file:
    contract_json = json.load(file)

contract_abi = contract_json['abi']
contract_bytecode = contract_json['bytecode']

# Initialize Web3 connection
w3 = Web3(Web3.HTTPProvider(host))

# Function to create and deploy the contract
def create_contract(w3, contract_abi, contract_bytecode, from_address):
    contract = w3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
    # Build transaction
    tx = contract.constructor().build_transaction({
        'from': from_address,
        'gas': 1500000,  # Gas limit
        'gasPrice': w3.to_wei('0', 'gwei'),
        'nonce': w3.eth.get_transaction_count(from_address),
    })
    
    # Sign the transaction
    private_key = "0x10302650bba084cb367619521b9879af3f2b9bba4533a6cb984e94764371c8a3"  # Add your private key here
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    
    # Send the transaction
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    # Wait for the transaction receipt
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    print(f"The transaction hash is: {w3.to_hex(tx_hash)}")
    return tx_receipt

# Main function to deploy the contract
def main():
    tx_receipt = create_contract(w3, contract_abi, contract_bytecode, address)
    print(f"Contract deployed at address: {tx_receipt.contractAddress}")

if __name__ == "__main__":
    main()
