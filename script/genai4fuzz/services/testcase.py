import json
import copy
import hashlib
from eth_abi import encode
from eth_utils import to_bytes
from loguru import logger
from pydantic import ValidationError
from typing import List, Any, Dict

from genai4fuzz.model.testcase import TestCaseModel
from genai4fuzz.utils.general import flatten_list, discard_fields
from genai4fuzz.config import Config
from genai4fuzz.services.sast import SastService

class TestCase(object):
    
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

    @staticmethod
    def try_to_adapt_json_testcase(json: list):
        if isinstance(json, dict):
            return json.get('TestCases') or json.get('TestCase', {})
        return json or {}
    
    @property
    def ENTITIES(self):
        return copy.deepcopy(self._ENTITIES)        

    def __init__(self, tc: dict) -> None:
        self._config = Config()
        self._sast_service = SastService()

        self.testcase = tc
        self._is_valid_struct = True
        if not self.is_valid_testcase_struct():
            self._is_valid_struct = False
            logger.error("TestCase struct does not respect JSON format or invalid data types")
            
        self._total_invalid_functions = 0
        self._total_invalid_args = 0
        self._total_args = 0
        self._total_functions = 0
        
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
                                                    
    def _encode_args(self, function_selector, tx):
        try:
            intTypes = [ "uint8", "uint16", "uint32", "uint64", "uint128", "uint256", "int8", "int16", "int32", "int64", "int128", "int256"]
            intArraysTypes = [ "uint8[]", "uint16[]", "uint32[]", "uint64[]", "uint128[]", "uint256[]", "int8[]", "int16[]", "int32[]", "int64[]", "int128[]", "int256[]"]
            strTypes = ['address', 'string']
                        
            _args = []
            func, types = self.interfaces[function_selector]
            logger.info(f"func {func}, types {types} args {tx}")
            args = tx
            if not any(t.endswith('[]') for t in types) and any(isinstance(i, list) for i in tx):
                args = flatten_list(tx)

            i = 0
            for type in types:
                if type in intTypes:
                    _args.append(int(args[i]))
                elif type in strTypes:
                    if type == "address":
                        agent = self._is_agent(args[i])
                        if agent is not None:
                            _args.append(str(agent))
                        else:
                            _args.append(str(args[i]))
                    else:
                        _args.append(str(args[i]))
                elif type == 'bool':
                    _args.append(str(args[i]).lower() in ['true', 'false'])
                elif type == 'bytes32[]':
                    if isinstance(args[i], list):
                        bytelist = []                        
                        for b in args[i]:
                            bytelist(self._convert_bytes(b))
                        _args.append(bytelist)
                    else:
                        raise ValueError("Not a list of bytes")
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
                            agent = self._is_agent(p)
                            if agent is not None:
                                tmp_args.append(str(agent))
                            else:
                                tmp_args.append(str(p))
                        _args.append(tmp_args)
                    else:
                        _args.append(args)
                elif type in intArraysTypes:
                    _args.append([int(item) for item in args[i]])
                    
                i += 1
            encoded_args = encode(types, _args)
            self._total_args += 1
            return encoded_args.hex()               
        except Exception as e:
            logger.error(f"Exeption {e}")
            self._total_invalid_args += 1
            return None

    def get_testcase_hash(self, fields_to_discard = []):
        obj_str = json.dumps(self.testcase, sort_keys=True)
        filtered_data = discard_fields(self.testcase, fields_to_discard)
        obj_str = json.dumps(filtered_data, sort_keys=True)
        return hashlib.sha256(obj_str.encode('utf-8')).hexdigest()

    def _inject_agents(self, json):
        json["Entities"] = self.ENTITIES

    def _is_agent(self, agent: str):
        try:
            index = int(agent[-1])
            if index not in {1, 2, 3, 4}:
                return None
            return self.ENTITIES[index - 1]['Contract']
        except (ValueError, IndexError):
            return None
        
    def _get_agent(self, agent: str):
        index = int(agent[-1])
        if index < 1 or index > 4:
            logger.warning("Invalid SmartianAgent id, defaulting to 1")
            index = 1
        return self.ENTITIES[index - 1]['Contract']
        
    def _process_deploy_elements(self, tc, with_args):
        deployTx = self._get_deploy_tx(tc)
        data = ""
        if with_args and deployTx.get('Params') is not None and len(deployTx.get('Params')) > 0:
            encoded = self._encode_args("constructor", deployTx['Params'])
            if encoded is not None:
                data = encoded
        
        return json.loads(f'''{{
            "TargetDeployer":"{self._get_agent(deployTx['From'])}",
            "TargetContract":"0x6b773032d99fb9aad6fc267651c446fa7f9301af",
            "DeployTx": {{
                "From":"{self._get_agent(deployTx['From'])}",
                "To":"0x6b773032d99fb9aad6fc267651c446fa7f9301af",
                "Value":"{deployTx['Value']}",
                "Data":"{data}",
                "Timestamp":"{deployTx['Timestamp']}",
                "Blocknum":"{deployTx['Blocknum']}",
                "Function":"constructor"
            }}}}
            ''')
        
    def _process_transaction(self, tx: dict, contract_abi, with_args):
        function_name = tx['Function']
        func_selector = self._sast_service.get_function_selector(contract_abi, function_name)
        if func_selector is None:
            logger.warning(f"Invalid function name ({function_name}), skiping transaction")
            self._total_invalid_functions += 1
            return None
        self._total_functions += 1        
        
        if function_name == "fallback" or function_name == "fallback()":
            function_name = f"{tx['Function']}"
        else:
            function_name = f"{tx['Function']}({func_selector})"

        data = func_selector
        if with_args and tx.get('Params') is not None and len(tx.get('Params')) > 0:
            encoded = self._encode_args(func_selector, tx['Params'])
            if encoded is not None:
                data += encoded
        return json.loads((f'''{{
            "From":"{self._get_agent(tx['From'])}",
            "To":"0x6b773032d99fb9aad6fc267651c446fa7f9301af",
            "Value":"{tx['Value']}",
            "Data":"{data}",
            "Timestamp":"{tx['Timestamp']}",
            "Blocknum":"{tx['Blocknum'] if tx.get('Blocknum') else "20000944"}",
            "Function":"{function_name}"
            }}
            '''))

    def is_valid_testcase_struct(self):
        try:
            testcase_data = self.testcase.get("TestCase", self.testcase)
            TestCaseModel(**testcase_data)
            return True
        except ValidationError as e:
            #print(f"Validation error: {e}")
            return False
                        
    def process_testcase(self, contract_abi, with_args):
        if not self._is_valid_struct:
            return None
        self.interfaces = self._sast_service.get_interface_from_abi(contract_abi)
        tc_json = {}
        self._inject_agents(tc_json)
        tc_json.update(self._process_deploy_elements(self.testcase, with_args))
        txs = []
        for tx in self._get_txs(self.testcase):
            tx_parsed = self._process_transaction(tx, contract_abi, with_args)
            if tx_parsed is not None:
                txs.append(self._process_transaction(tx, contract_abi, with_args))
        tc_json['Txs'] = txs
        return tc_json

    def get_validation_totals(self):
        return [(self._total_args, self._total_invalid_args),
                 (self._total_functions, self._total_invalid_functions)]
