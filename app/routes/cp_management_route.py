from fastapi import FastAPI, APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models.cp_collection_model import *
from app.config.private import collection_points
from bson import ObjectId

cpManagementRoute = APIRouter()

# API endpoint to get all transactions based on wallet address
@cpManagementRoute.post("/post-cp-to-cf", tags=["Collection Point Management"], summary="Returns MongoId of the stored CP")
async def post_cp_to_cf(cp_data: CPData, x_token: str = Header(...)):
    # Check if the x_token is correct
    if x_token != "block_concur":
        raise HTTPException(status_code=403, detail="Invalid token")
    
    # Convert the Pydantic model to a dictionary for MongoDB insertion
    cp_dict = cp_data.dict(by_alias=True)
    
    # Insert the data into the collection
    insert_result = collection_points.insert_one(cp_dict)

    collection_points.update_one({"_id": insert_result.inserted_id}, {"$set":{"blockchain_status": "not deployed","contract_address": None,"txn_hash": None}})
    
    # Return the inserted ObjectId
    return {"cp_contract_id": str(insert_result.inserted_id)}

# GET API to check the contract status
@cpManagementRoute.get("/get-cp-status/{cp_contract_id}", response_model=CPStatusResponse, tags=["Collection Point Management"], summary="Returns contract deployment status")
async def get_cp_status(cp_contract_id: str , x_token:str=Header(...)):
    
    if x_token != "block_concur":
        raise HTTPException(status_code=403, detail="Invalid token")
    
    # Query the document based on cp_contract_id
    cp_data = collection_points.find_one({"_id": ObjectId(cp_contract_id)})
    
    if not cp_data:
        raise HTTPException(status_code=404, detail="Collection point not found")
    
    blockchain_status = cp_data.get("blockchain_status", "not deployed")
    print(blockchain_status)
    contract_address = cp_data.get("contract_address")
    txn_hash = cp_data.get("txn_hash")

    # Check the status and return appropriate message
    if blockchain_status == "not deployed":
        return {
            "message": "Contract not deployed yet, please query after 30 mins",
            "blockchain_status": blockchain_status
        }
    elif blockchain_status == "deploying":
        return {
            "message": "Contract is being deployed, please wait for the completion",
            "blockchain_status": blockchain_status
        }
    elif blockchain_status == "deployed":
        return {
            "message": "Contract Deployed",
            "txn_hash": txn_hash,
            "contract_address": contract_address,
            "blockchain_status": blockchain_status
        }
    else:
        raise HTTPException(status_code=500, detail="Unknown blockchain status")

