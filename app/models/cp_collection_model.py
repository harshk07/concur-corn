from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PurposeMandatory(BaseModel):
    mandatory_text: str
    mandatory_status: bool = False

class PurposeLegal(BaseModel):
    legal_text: str
    legal_status: bool = False

class Purpose(BaseModel):
    purpose_id: str
    purpose_description: str
    purpose_language: str
    translated_purpose_id: str
    purpose_expiry: int
    purpose_retention: int
    purpose_mandatory: PurposeMandatory
    purpose_revokable: bool = False
    purpose_encrypted: bool = False
    purpose_cross_border: bool = False
    purpose_shared: bool = False
    purpose_legal: PurposeLegal

class DataElement(BaseModel):
    data_element: str
    data_element_collection_status: str
    data_element_title: str
    data_element_description: str
    data_owner: List[str]
    legal_basis: bool = False
    retention_period: int
    cross_border: bool = False
    sensitive: bool = False
    encrypted: bool = False
    expiry: int
    purposes: List[Purpose]

class CPData(BaseModel):
    org_id: str
    application_id: str
    cp_id: str
    cp_name: str
    cp_status: str
    data_elements: List[DataElement]
    registered_at: str
    cp_url: str

# Model for Response
class CPStatusResponse(BaseModel):
    message: str
    txn_hash: Optional[str] = None
    contract_address: Optional[str] = None
    blockchain_status: str


    # published_in_blockchain: bool = False
    # blockchain_status: str
    # contract_address: str = None
    # txn_hash: str = None