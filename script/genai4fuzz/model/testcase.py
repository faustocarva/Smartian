from typing import List, Optional, Any, Union
import re
from pydantic import BaseModel, root_validator, ValidationError, conint, validator

UInt256 = conint(ge=0, le=(2**256 - 1))

class DeployTx(BaseModel):
    From: str
    Value: UInt256
    Function: str
    Params: Optional[list[Any]] = None
    Timestamp: str
    Blocknum: str


    @validator('Value', pre=True)
    def validate_value_is_integer(cls, v):
        # For string inputs like "0.0"
        if isinstance(v, str):
            if '.' in v:
                raise ValueError('Value must be an integer, not a float')
            try:
                v = int(v)
            except ValueError:
                raise ValueError('Value must be a valid integer')
        # For float inputs like 0.0
        elif isinstance(v, float):
            if v != int(v):
                raise ValueError('Value must be an integer, not a float')
            v = int(v)
        return v
        
    @validator('From')
    def validate_from_field(cls, v):
        if not re.match(r'SmartianAgent\d+$', v):
            raise ValueError('From field must be in format SmartianAgent followed by numbers')
        return v

    
    
    @validator('Timestamp', 'Blocknum')
    def validate_numeric_fields(cls, v):
        if not v.isdigit():  # This ensures string contains only digits
            raise ValueError('Field must contain only numeric characters')
        return v

class Tx(BaseModel):
    From: str
    Value: UInt256
    Function: str
    Params: Optional[list[Any]] = None
    Timestamp: str
    Blocknum: str

    @validator('Value', pre=True)
    def validate_value_is_integer(cls, v):
        # For string inputs like "0.0"
        if isinstance(v, str):
            if '.' in v:
                raise ValueError('Value must be an integer, not a float')
            try:
                v = int(v)
            except ValueError:
                raise ValueError('Value must be a valid integer')
        # For float inputs like 0.0
        elif isinstance(v, float):
            if v != int(v):
                raise ValueError('Value must be an integer, not a float')
            v = int(v)
        return v
    

    @validator('From')
    def validate_from_field(cls, v):
        if not re.match(r'SmartianAgent\d+$', v):
            raise ValueError('From field must be in format SmartianAgent followed by numbers')
        return v

    
    @validator('Timestamp', 'Blocknum')
    def validate_numeric_fields(cls, v):
        if not v.isdigit():  # This ensures string contains only digits
            raise ValueError('Field must contain only numeric characters')
        return v
    
class TestCaseModel(BaseModel):
    DeployTx: DeployTx
    Txs: List[Tx]
