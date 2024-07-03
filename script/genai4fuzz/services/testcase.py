import os
import time
import json
import re
import copy
from eth_abi import encode
from eth_utils import function_signature_to_4byte_selector, to_checksum_address, to_bytes, to_int, to_hex
from loguru import logger

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
        
    def get_interface_from_abi(self, abi):
        abi = json.loads(abi)        
        interface = {}      
        for field in abi:
            if field['type'] == 'function':
                function_name = field['name']
                function_inputs = []
                signature = function_name + '('
                for i in range(len(field['inputs'])):
                    input_type = field['inputs'][i]['type']
                    function_inputs.append(input_type)
                    signature += input_type
                    if i < len(field['inputs']) - 1:
                        signature += ','
                signature += ')'
                hash = function_signature_to_4byte_selector(signature).hex()
                interface[hash] = function_name, function_inputs
            elif field['type'] == 'constructor':
                function_inputs = []
                for i in range(len(field['inputs'])):
                    input_type = field['inputs'][i]['type']
                    function_inputs.append(input_type)
                interface['constructor'] = 'constructor', function_inputs, 
            elif field['type'] == 'fallback':
                func_signature = 'fallback()'
                hash = function_signature_to_4byte_selector(func_signature).hex()
                interface[hash] = "fallback",[]

        return interface
        

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
                payable = " payable " if item.get('payable', False) or item.get('stateMutability') == 'payable' else ""
                func_signature = item['name'] + '(' + ','.join([input['type'] for input in item['inputs']]) + ')' + payable                
                func_selector = function_signature_to_4byte_selector(func_signature)
            elif item.get('type') == 'fallback':
                func_signature = 'fallback()'
                func_selector = function_signature_to_4byte_selector(func_signature)
            else:
                continue
            
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
                selector = function_signature_to_4byte_selector(func_signature).hex()
            elif item.get('type') == 'fallback' and (function == "fallback" or function == "fallback()"):
                func_signature = 'fallback()'
                selector = function_signature_to_4byte_selector(func_signature).hex()
        return selector
               

    # Mapping from Solidity types to conversion functions
    def _convert_bytes(self, value):
        if value.startswith("0x"):
            padded_string = value[2:].ljust(32, '0')[:32]
            return to_bytes(hexstr=padded_string)
        return bytes(value, 'utf-8')

                
    def encodeArgs(self, function_selector, tx):
        try:
            intTypes = [ "uint8", "uint16", "uint32", "uint64", "uint128", "uint256", "int8", "int16", "int32", "int64", "int128", "int256"]
            intArraysTypes = [ "uint8[]", "uint16[]", "uint32[]", "uint64[]", "uint128[]", "uint256[]", "int8[]", "int16[]", "int32[]", "int64[]", "int128[]", "int256[]"]
            strTypes = ['address', 'string']
                        
            _args = []
            func, types = self.interfaces[function_selector]
            print(f"func {func}, types {types} args {tx}")
            args = tx
            if not any(s.endswith('[]') for s in types) and any(isinstance(i, list) for i in tx):
                args = [item for sublist in tx for item in sublist]

            i = 0
            for type in types:
                if type in intTypes:
                    #print(args[i])
                    _args.append(int(args[i]))
                elif type in strTypes:
                    if type == "address":
                        agent = self.isAgent(args[i])
                        # print(agent)
                        if agent is not None:
                            _args.append(str(agent))
                        else:
                            _args.append(str(args[i]))                            
                    else:
                        _args.append(str(args[i]))
                elif type == 'bool':
                    _args.append(str(args[i]).lower() in ['true', 'false'])
                elif type == 'bytes32' or type == 'bytes':
                    _args.append(self._convert_bytes(args[i]))
                elif type == 'address[]':
                    if isinstance(args[i], list):
                        _args.append(args[i])
                    else:
                        _args.append(args)
                elif type in intArraysTypes:
                    _args.append([int(item) for item in args[i]])
                    
                i += 1
            #_args = [type_conversion[solidity_type](args[i]) for i, solidity_type in enumerate(types)]
            # print(_args)
            
            encoded_args = encode(types, _args)
            return encoded_args.hex()               
        except Exception as e:
            logger.error(f"Exeption {e}, missing tx parameters")
            return None
        
                                    
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
        
    def processTestCase(self, tc: dict, contract_abi, with_args):
        self.interfaces = self.get_interface_from_abi(contract_abi)
        tc_json = {}
        self.injectAgents(tc_json)
        tc_json.update(self.processDeployElements(tc))
        txs = []
        for tx in self._getTxs(tc):
            tx_parsed = self.processTransaction(tx, contract_abi, with_args)
            if tx_parsed is not None:
                txs.append(self.processTransaction(tx, contract_abi, with_args))
        tc_json['Txs'] = txs
        return tc_json
        
    def isAgent(self, agent: str):
        index = int(agent[-1])
        if index < 1 or index > 4:
            return None
        return self.ENTITIES[index - 1]['Contract']


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
        
    def processTransaction(self, tx: dict, contract_abi, with_args):
        function_name = tx['Function']
        func_selector = self.getFunctionSelector(contract_abi, function_name)
        if func_selector is None:
            logger.warning("Invalid function name, skiping transaction")
            return None
        
        if function_name == "fallback" or function_name == "fallback()":
            function_name = f"{tx['Function']}"
        else:
            function_name = f"{tx['Function']}({func_selector})"

        data = func_selector
        if with_args and tx.get('Params') is not None and len(tx.get('Params')) > 0:
            encoded = self.encodeArgs(func_selector, tx['Params'])
            if encoded is not None:
                data += encoded
        return json.loads((f'''{{
            "From":"{self.getAgent(tx['From'])}",
            "To":"0x6b773032d99fb9aad6fc267651c446fa7f9301af",
            "Value":"{tx['Value']}",
            "Data":"{data}",
            "Timestamp":"{tx['Timestamp']}",
            "Blocknum":"{tx['Blocknum']}",
            "Function":"{function_name}"
            }}
            '''))