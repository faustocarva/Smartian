import os
import time
import json
import re
import copy
from eth_abi import encode
from eth_utils import function_signature_to_4byte_selector, to_bytes
from loguru import logger
from slither import Slither

from genai4fuzz.utils.general import flatten_list
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
        #self._slither = Slither()

    def _get_deploy_tx(self, tc):
            if "TestCase" in tc:
                return tc['TestCase'].get('DeployTx')
            else:
                return tc.get('DeployTx')
            
    def _get_txs(self, tc):
            if "TestCase" in tc:
                return tc['TestCase'].get('Txs')
            else:
                return tc.get('Txs')

    def _convert_bytes(self, value):
        if value.startswith("0x"):
            padded_string = value[2:].ljust(32, '0')[:32]
            return to_bytes(hexstr=padded_string)
        return bytes(value, 'utf-8')

    def get_function_modifiers(self, contract_file, target_functions):
        slither = Slither(contract_file)
        modifiers = {}
        
        for contract in slither.contracts_derived:
            for function in contract.functions:
                param_types = [param.type.__str__() for param in function.parameters]
                signature = f"{function.name}({','.join(param_types)})"
                if function.visibility == 'public' and signature in target_functions:
                    for modifier in function.modifiers:
                        modifiers[signature] = [modifier.name] + modifiers.get(signature, [])
                                           
        for key in modifiers.keys():
            i = target_functions.index(key)
            modifiers_str = ' '.join([modifier_str for modifier_str in modifiers[key]])
            target_functions[i] = f"{target_functions[i]} {modifiers_str}"

        return target_functions

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
        
    def get_functions_from_ABI(self, abi: str):
        abi = json.loads(abi)
        functions = []
        for item in abi:
            if item.get('type') == 'function':
                payable = " payable " if item.get('payable', False) or item.get('stateMutability') == 'payable' else ""
                func_signature = item['name'] + '(' + ','.join([input['type'] for input in item['inputs']]) + ')' + payable
            elif item.get('type') == 'constructor':
                func_signature = 'constructor' + '(' + ','.join([input['type'] for input in item['inputs']]) + ')'
            elif item.get('type') == 'fallback':
                func_signature = 'fallback()'
            else:
                continue
            
            functions.append(f'{func_signature}')

        return functions
                
    def get_function_selector(self, abi: str, function: str):
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
            elif item.get('type') == 'constructor' and item.get('name') == function:
                func_signature = "constructor" + '(' + ','.join([input['type'] for input in item['inputs']]) + ')'
                selector = function_signature_to_4byte_selector(func_signature).hex()
                
        return selector
                                
    def encode_args(self, function_selector, tx):
        try:
            intTypes = [ "uint8", "uint16", "uint32", "uint64", "uint128", "uint256", "int8", "int16", "int32", "int64", "int128", "int256"]
            intArraysTypes = [ "uint8[]", "uint16[]", "uint32[]", "uint64[]", "uint128[]", "uint256[]", "int8[]", "int16[]", "int32[]", "int64[]", "int128[]", "int256[]"]
            strTypes = ['address', 'string']
                        
            _args = []
            func, types = self.interfaces[function_selector]
            print(f"func {func}, types {types} args {tx}")
            args = tx
            if not any(t.endswith('[]') for t in types) and any(isinstance(i, list) for i in tx):
                args = flatten_list(tx)
                #args = [item for sublist in tx for item in sublist]

            i = 0
            for type in types:
                if type in intTypes:
                    _args.append(int(args[i]))
                elif type in strTypes:
                    if type == "address":
                        agent = self.is_agent(args[i])
                        if agent is not None:
                            _args.append(str(agent))
                        else:
                            _args.append(str(args[i]))
                    else:
                        _args.append(str(args[i]))
                elif type == 'bool':
                    _args.append(str(args[i]).lower() in ['true', 'false'])
                elif type == 'bytes32' or type == 'bytes':
                    if isinstance(args[i], list):
                        if len(args[i]) > 1:
                            raise ValueError("Invalid size")
                        _args.append(self._convert_bytes(args[i][0]))
                    else:
                        _args.append(self._convert_bytes(args[i]))
                elif type == 'address[]':
                    if isinstance(args[i], list):
                        tmp_args = []
                        for p in args[i]:
                            agent = self.is_agent(p)
                            if agent is not None:
                                tmp_args.append(str(agent))
                            else:
                                _args.append(str(p))                        
                        _args.append(tmp_args)
                    else:
                        _args.append(args)
                elif type in intArraysTypes:
                    _args.append([int(item) for item in args[i]])
                    
                i += 1
            encoded_args = encode(types, _args)
            return encoded_args.hex()               
        except Exception as e:
            logger.error(f"Exeption {e}")
            return None

    def inject_agents(self, json):
        json["Entities"] = self.ENTITIES

    def validate_testcase_struct(self, tc):        
        if tc.get('TestCase') and tc['TestCase'].get('DeployTx') and tc['TestCase'].get('Txs'):
            return True
        elif tc.get('DeployTx') and tc.get('Txs'):
            return True
        else:
            return False                
        
    def process_testcase(self, tc: dict, contract_abi, with_args):
        self.interfaces = self.get_interface_from_abi(contract_abi)
        tc_json = {}
        self.inject_agents(tc_json)
        tc_json.update(self.process_deploy_elements(tc, contract_abi, with_args))
        txs = []
        for tx in self._get_txs(tc):
            tx_parsed = self.process_transaction(tx, contract_abi, with_args)
            if tx_parsed is not None:
                txs.append(self.process_transaction(tx, contract_abi, with_args))
        tc_json['Txs'] = txs
        return tc_json
        
    def is_agent(self, agent: str):
        index = int(agent[-1])
        if index < 1 or index > 4:
            return None
        return self.ENTITIES[index - 1]['Contract']

    def get_agent(self, agent: str):
        index = int(agent[-1])
        if index < 1 or index > 4:
            logger.warning("Invalid SmartianAgent id, defaulting to 1")
            index = 1
        return self.ENTITIES[index - 1]['Contract']
        
    def process_deploy_elements(self, tc, contract_abi, with_args):
        deployTx = self._get_deploy_tx(tc)
        data = ""
        if with_args and deployTx.get('Params') is not None and len(deployTx.get('Params')) > 0:
            encoded = self.encode_args("constructor", deployTx['Params'])
            if encoded is not None:
                data = encoded
        
        return json.loads(f'''{{
            "TargetDeployer":"{self.get_agent(deployTx['From'])}",
            "TargetContract":"0x6b773032d99fb9aad6fc267651c446fa7f9301af",
            "DeployTx": {{
                "From":"{self.get_agent(deployTx['From'])}",
                "To":"0x6b773032d99fb9aad6fc267651c446fa7f9301af",
                "Value":"{deployTx['Value']}",
                "Data":"{data}",
                "Timestamp":"{deployTx['Timestamp']}",
                "Blocknum":"{deployTx['Blocknum']}",
                "Function":"constructor"
            }}}}
            ''')
        
    def process_transaction(self, tx: dict, contract_abi, with_args):
        function_name = tx['Function']
        func_selector = self.get_function_selector(contract_abi, function_name)
        if func_selector is None:
            logger.warning("Invalid function name, skiping transaction")
            return None
        
        if function_name == "fallback" or function_name == "fallback()":
            function_name = f"{tx['Function']}"
        else:
            function_name = f"{tx['Function']}({func_selector})"

        data = func_selector
        if with_args and tx.get('Params') is not None and len(tx.get('Params')) > 0:
            encoded = self.encode_args(func_selector, tx['Params'])
            if encoded is not None:
                data += encoded
        return json.loads((f'''{{
            "From":"{self.get_agent(tx['From'])}",
            "To":"0x6b773032d99fb9aad6fc267651c446fa7f9301af",
            "Value":"{tx['Value']}",
            "Data":"{data}",
            "Timestamp":"{tx['Timestamp']}",
            "Blocknum":"{tx['Blocknum'] if tx.get('Blocknum') else "20000944"}",
            "Function":"{function_name}"
            }}
            '''))
