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
            return match.group(0)
        except json.JSONDecodeError:
            return None
        
    def getFunctionsFromABI(self, abi: str, with_selector: bool):
        abi = json.loads(abi)                
        functions = []
        for item in abi:
            if item.get('type') == 'function':
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
                
    def getFunctionSelector(self, abi: str, function: str):
        abi = json.loads(abi)
        selector = None
        for item in abi:
            #Smartian has a bug with functions with same name and different args, loop til the end, as smartian to make same selector
            if item.get('name') == function:
                func_signature = item['name'] + '(' + ','.join([input['type'] for input in item['inputs']]) + ')'
                selector = eth_utils.function_signature_to_4byte_selector(func_signature).hex()
            elif item.get('type') == 'fallback' and (function == "fallback" or function == "fallback()"):
                func_signature = 'fallback()'
                selector = eth_utils.function_signature_to_4byte_selector(func_signature).hex()
        return selector
                    
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

    def _getDeployTx(self, tc):
            if "TestCase" in tc:
                return tc['TestCase'].get('DeployTx')
            else:
                return tc.get('DeployTx')
            
    def _getTxs(self, tc):
            if "TestCase" in tc:
                return tc['TestCase'].get('Txs')
            else:
                return tc.get('Txs')

    def validateTestCaseStruct(self, tc):        
        if tc.get('TestCase') and tc['TestCase'].get('DeployTx') and tc['TestCase'].get('Txs'):
            return True
        elif tc.get('DeployTx') and tc.get('Txs'):
            return True
        else:
            return False                
        
    def processTestCase(self, tc: dict, contract_abi):
        tc_json = {}
        self.injectAgents(tc_json)
        tc_json.update(self.processDeployElements(tc))
        txs = []
        for tx in self._getTxs(tc):
            tx_parsed = self.processTransaction(tx, contract_abi)
            if tx_parsed is not None:
                txs.append(self.processTransaction(tx, contract_abi))
        tc_json['Txs'] = txs
        return tc_json
        

    def getAgent(self, agent: str):
        index = int(agent[-1])
        if index < 1 or index > 4:
            logger.warning("Invalid SmartianAgent id, defaulting to 1")
            index = 1
        return self.ENTITIES[index - 1]['Contract']
        
    def processDeployElements(self, tc):
        deployTx = self._getDeployTx(tc)
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
        
    def processTransaction(self, tx: dict, contract_abi):
        function_name = tx['Function']
        func_selector = self.getFunctionSelector(contract_abi, function_name)
        if func_selector is None:
            logger.warning("Invalid function name, skiping transaction")
            return None
        
        if function_name == "fallback" or function_name == "fallback()":
            function_name = f"{tx['Function']}"
        else:
            function_name = f"{tx['Function']}({func_selector})"
            
        return json.loads((f'''{{
            "From":"{self.getAgent(tx['From'])}",
            "To":"0x6b773032d99fb9aad6fc267651c446fa7f9301af",
            "Value":"{tx['Value']}",
            "Data":"{func_selector}",
            "Timestamp":"{tx['Timestamp']}",
            "Blocknum":"{tx['Blocknum']}",
            "Function":"{function_name}"
            }}
            '''))