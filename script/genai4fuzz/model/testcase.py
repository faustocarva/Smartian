from typing import List, Optional, Any, Dict, Union
from pydantic import BaseModel, Field, ValidationError, conint, validator
from genai4fuzz.utils.general import convert_to_wei
import re

UInt256 = conint(ge=0, le=(2**256 - 1))

class BaseTxModel(BaseModel):
    From: str
    Value: UInt256
    Function: str
    Params: Optional[List[Any]] = None
    Timestamp: str
    Blocknum: str

    @validator('Value', pre=True)
    def validate_value_is_integer(cls, v):
        try:
            return convert_to_wei(v)
        except ValueError as e:
            raise ValueError(f"Invalid value for 'Value': {e}")
        
    @validator('From')
    def validate_from_field(cls, v):
        if not re.match(r'SmartianAgent\d+$', v):
            raise ValueError("'From' field must be in format 'SmartianAgentX' where X is one or more digits")
        return v
        
    @validator('Timestamp', 'Blocknum')
    def validate_numeric_fields(cls, v):
        if not v.isdigit():
            raise ValueError(f"Field must contain only numeric characters, got '{v}'")
        return v

class DeployTx(BaseTxModel):
    # Inherits all validators from BaseTxModel
    pass

class Tx(BaseTxModel):
    # Inherits all validators from BaseTxModel
    pass
    
class TestCaseModel(BaseModel):
    DeployTx: DeployTx
    Txs: List[Tx]