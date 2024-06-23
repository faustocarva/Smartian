from loguru import logger
import os
import time
import json
import re
import eth_abi
import eth_utils
import copy


from genai4fuzz.utils.singleton import SingletonMeta
from genai4fuzz.config import Config

class TestCaseService(metaclass=SingletonMeta):
    
    _ENTITIES = [
            {
                "Balance": "10000000000000000000000",
                "Account": "0xb7705ae4c6f81b66cdb323c65f4e8133690fc099",
                "Agent": "SmartianAgent",
                "Contract": "0x24cd2edba056b7c654a50e8201b619d4f624fdda"
            },
            {
                "Balance": "10000000000000000000000",
                "Account": "0x00120000000000000000000000000000000001d2",
                "Agent": "SmartianAgent",
                "Contract": "0x118a2c24808934116e6ab4c00ff48145d23b09e1"
            },
            {
                "Balance": "10000000000000000000000",
                "Account": "0x001200000000000000000000000000000000021c",
                "Agent": "SmartianAgent",
                "Contract": "0x226cc61b3eac93cc2cc9d6cb8d61856670d50fad"
            },
            {
                "Balance": "10000000000000000000000",
                "Account": "0x0012000000000000000000000000000000000229",
                "Agent": "SmartianAgent",
                "Contract": "0x33b808a5ae24c410e8739b5ca2d5ef3931d3e09f"
            }
        ]

    @property
    def ENTITIES(self):
        return copy.deepcopy(self._ENTITIES)
    
    def __init__(self) -> None:
        self._config = Config()

    def is_valid_json(self, json_string: str) -> bool:
        try:
            json.loads(json_string)
            return True
        except Exception as e:
            #logger.debug(f"Invalid JSON: {e}")
            return False
        
        
    def json_from_text(self, text: str):
        match = re.search(r'\[[\s\S]*\]', text)
        if not match:
            return None

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        
    def getFunctionsFromABI(self, abi: str, with_selector: bool):
        abi = json.loads(abi)                
        functions = []
        for item in abi:
            if item.get('type') == 'function':# or item.get('type') == 'fallback':
                func_signature = item['name'] + '(' + ','.join([input['type'] for input in item['inputs']]) + ')'
                func_selector = eth_utils.function_signature_to_4byte_selector(func_signature)
            elif item.get('type') == 'fallback':
                func_signature = 'fallback()'
                func_selector = eth_utils.function_signature_to_4byte_selector(func_signature)
            else:
                break
            
            if with_selector:
                functions.append(f'{func_selector.hex()}, {func_signature}')
            else:
                functions.append(f'{func_signature}')                
            
        return functions        
                
    def _validateFunctionSelector(self, abi: list, calldata: str):
        function_selector = calldata[:8]        
        function_abi = None
        for item in abi:
            if item.get('type') == 'function':
                func_signature = item['name'] + '(' + ','.join([input['type'] for input in item['inputs']]) + ')'
                func_selector = eth_utils.function_signature_to_4byte_selector(func_signature)
                if function_selector.lower() == func_selector.hex().lower():
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
            logger.info(f"Validating function : {self._validateFunctionSelector(abi, tx['Data'])}")
        
    def injectAgents(self, json):
        json["Entities"] = self.ENTITIES

    def validateTestCaseStruct(self, tc):
        if tc.get('TestCase') and tc['TestCase'].get('DeployTx') and tc['TestCase'].get('Txs'):
            return True
        else:
            return False
        
        
    def processTestCase(self, tc: dict):
        tc_json = {}
        self.injectAgents(tc_json)
        tc_json.update(self.processDeployElements(tc['TestCase']['DeployTx']))
        txs = []
        for tx in tc['TestCase']['Txs']:
            txs.append(self.processTransaction(tx))
        tc_json['Txs'] = txs
        return tc_json
        

    def getAgent(self, agent: str):
        return self.ENTITIES[int(agent[-1]) - 1]['Contract']
        
    def processDeployElements(self, deployTx: dict):
        return json.loads(f'''{{
            "TargetDeployer":"{self.getAgent(deployTx['From'])}",
            "TargetContract":"0x6b773032d99fb9aad6fc267651c446fa7f9301af",
            "DeployTx": {{
                "From":"{self.getAgent(deployTx['From'])}",
                "To":"0x6b773032d99fb9aad6fc267651c446fa7f9301af",
                "Value":"{deployTx['Value']}",
                "Data":"",
                "Timestamp":"{deployTx['Timestamp']}",
                "Blocknum":"{deployTx['Blocknum']}",
                "Function":"constructor"
            }}}}
            ''')
        
    def processTransaction(self, tx: dict):
        return json.loads((f'''{{
            "From":"{self.getAgent(tx['From'])}",
            "To":"0x6b773032d99fb9aad6fc267651c446fa7f9301af",
            "Value":"{tx['Value']}",
            "Data":"",
            "Timestamp":"{tx['Timestamp']}",
            "Blocknum":"{tx['Blocknum']}",
            "Function":"{tx['Function']}"
            }}
            '''))