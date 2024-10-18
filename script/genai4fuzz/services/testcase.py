import json
import re
import copy
from eth_abi import encode
from eth_utils import function_signature_to_4byte_selector, to_bytes
from loguru import logger
from slither import Slither

from genai4fuzz.utils.general import flatten_list, is_valid_json, json_from_text
from genai4fuzz.utils.singleton import SingletonMeta
from genai4fuzz.config import Config
from genai4fuzz.services.sast import SastService

#class TestCaseService(metaclass=SingletonMeta):
class TestCase:
    
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

    def __init__(self, tc: dict) -> None:
        self._config = Config()
        self._sast_service = SastService()
        self.testcase = tc
        self.total_invalid_json = 0
        self.total_invalid_struct = 0
        self.total_invalid_function = 0
        self.total_invalid_args = 0
        
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
                                                    
    def encode_args(self, function_selector, tx):
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
                            agent = self.is_agent(p)
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
            return encoded_args.hex()               
        except Exception as e:
            logger.error(f"Exeption {e}")
            return None

    def inject_agents(self, json):
        json["Entities"] = self.ENTITIES

    def validate_testcase_struct(self):
        if self.testcase.get('TestCase') and self.testcase['TestCase'].get('DeployTx') and self.testcase['TestCase'].get('Txs'):
            return True
        elif self.testcase.get('DeployTx') and self.testcase.get('Txs'):
            return True
        else:
            return False                
        
    def process_testcase(self, contract_abi, with_args):
        self.interfaces = self._sast_service.get_interface_from_abi(contract_abi)
        tc_json = {}
        self.inject_agents(tc_json)
        tc_json.update(self.process_deploy_elements(self.testcase, contract_abi, with_args))
        txs = []
        for tx in self._get_txs(self.testcase):
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
        func_selector = self._sast_service.get_function_selector(contract_abi, function_name)
        if func_selector is None:
            logger.warning(f"Invalid function name ({function_name}), skiping transaction")
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
