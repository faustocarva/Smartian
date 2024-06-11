from loguru import logger
import os
import time
import json

import eth_abi
import eth_utils


from genai4fuzz.utils.singleton import SingletonMeta
from genai4fuzz.config import Config

class TestCaseService(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._config = Config()

    def is_valid_json(self, json_string: str) -> bool:
        try:
            json.loads(json_string)
            return True
        except ValueError as e:
            print(f"Invalid JSON: {e}")
            return False
        
    def getFunctionsFromABI(self, abi: str):
        abi = json.loads(abi)                
        functions = []
        for item in abi:
            if item.get('type') == 'function':
                func_signature = item['name'] + '(' + ','.join([input['type'] for input in item['inputs']]) + ')'
                func_selector = eth_utils.function_signature_to_4byte_selector(func_signature)
                functions.append(f'Function Selector: {func_selector.hex()} Function Signature: {func_signature}')        
        return functions        
                
    def _validateFunctionSelector(self, abi: list, calldata: str):
        function_selector = calldata[:8]        
        function_abi = None
        for item in abi:
            if item.get('type') == 'function':
                func_signature = item['name'] + '(' + ','.join([input['type'] for input in item['inputs']]) + ')'
                func_selector = eth_utils.function_signature_to_4byte_selector(func_signature)
                #print('---------------')                
                #print(function_selector)                
                #print('---------------')                                
                if function_selector.lower() == func_selector.hex().lower():
                    #print(f'{function_selector.lower()} == {func_selector.hex().lower()}')                                    
                    function_abi = item
                    return func_signature

        if function_abi is None:
            raise Exception("Function selector not found in ABI")
        
    def validateTestCaseTxs(self, test_case: str, contract_abi: str):
        # 1. Validate From (must be from entities) and To (must the target)
        # 2. Data must be function selector and arguments
        test_case_file = open(test_case, "r").read()
        test_case = json.loads(test_case_file)
        abi = json.loads(contract_abi)        
        for tx in test_case['Txs']:
            #print(tx['Data'])
            logger.info(f"Validating function : {self._validateFunctionSelector(abi, tx['Data'])}")
        