from typing import List, Optional, Any, Union
from pydantic import BaseModel, root_validator, ValidationError, conint

UInt256 = conint(ge=0, le=(2**256 - 1))

class DeployTx(BaseModel):
    From: str
    Value: UInt256
    Function: str
    Params: Optional[list[Any]] = None
    Timestamp: str
    Blocknum: str

class Tx(BaseModel):
    From: str
    Value: UInt256
    Function: str
    Params: Optional[list[Any]] = None
    Timestamp: str
    Blocknum: str

class TestCaseModel(BaseModel):
    DeployTx: DeployTx
    Txs: List[Tx]
