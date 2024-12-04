from typing import List, Optional, Any, Union
from pydantic import BaseModel, root_validator, ValidationError

class DeployTx(BaseModel):
    From: str
    Value: str
    Function: str
    Params: Optional[list[Any]] = None
    Timestamp: str
    Blocknum: str

class Tx(BaseModel):
    From: str
    Value: str
    Function: str
    Params: Optional[list[Any]] = None
    Timestamp: str
    Blocknum: str

class TestCaseModel(BaseModel):
    DeployTx: DeployTx
    Txs: List[Tx]
