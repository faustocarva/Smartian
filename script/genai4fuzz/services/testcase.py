import json
import copy
import hashlib
from eth_abi import encode
from eth_utils import to_bytes
from loguru import logger
from pydantic import ValidationError
from typing import List, Any, Dict

from genai4fuzz.model.testcase import TestCaseModel
from genai4fuzz.utils.general import flatten_list, discard_fields, convert_to_wei
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
    def try_to_adapt_json_testcase(json: Any):
        if isinstance(json, dict):
            return json.get('TestCases') or json.get('TestCase', {})
        return json or {}
        
    @property
    def ENTITIES(self):
        return self._entities_copy

    def __init__(self, tc: dict) -> None:
        self._entities_copy = copy.deepcopy(self._ENTITIES)
                
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

    def _encode_args(self, function_selector: str, tx: list):
        """
        Encode function arguments for contract interaction.
        
        Args:
            function_selector: The function selector string
            tx: List of arguments to encode
                
        Returns:
            Encoded arguments as hex string or None if encoding fails
        """        
        try:
            # Type definitions
            INT_TYPES = [
                "uint8", "uint16", "uint32", "uint64", "uint128", "uint256",
                "int8", "int16", "int32", "int64", "int128", "int256"
            ]
            INT_ARRAY_TYPES = [f"{t}[]" for t in INT_TYPES]
            STR_TYPES = ['address', 'string']
            STR_ARRAY_TYPES = ['string[]']
            BOOL_ARRAY_TYPES = ['bool[]']
            BYTES_ARRAY_TYPES = ['bytes[]', 'bytes32[]']
            BYTES_TYPES = ['bytes32', 'bytes4', 'bytes']
                            
            _args = []
            func, types = self.interfaces[function_selector]

            # Handle argument flattening if needed
            args = tx

            self._total_args += 1
            
            if not any(t.endswith('[]') for t in types) and any(isinstance(i, list) for i in tx):
                args = flatten_list(tx)
            elif len(tx) == 1 and isinstance(tx[0], list) and len(types) == len(tx[0]):
                args = tx[0]  # Unwrap one level if necessary                

            logger.info(f"Encoding function: {func}, types: {types}, args: {args}")

            if len(types) != len(args):
                raise ValueError(f"Dimensional error: Expected {len(types)} arguments but got {len(args)}")
            
            for i, (type_, arg) in enumerate(zip(types, args)):

                # Integer types
                if type_ in INT_TYPES:
                    _args.append(int(eval(arg)) if isinstance(arg, str) else int(arg))
                
                # String and address types
                elif type_ in STR_TYPES:
                    if type_ == "address":
                        agent_addr = self._get_agent(arg)
                        final_addr = agent_addr if agent_addr is not None else arg
                        if isinstance(final_addr, str) and not final_addr.startswith('0x'):
                            final_addr = '0x' + final_addr
                        if isinstance(final_addr, str) and final_addr.startswith('0x'):
                            addr_hex = final_addr[2:].lower().zfill(40)
                            final_addr = '0x' + addr_hex
                        _args.append(final_addr)
                    else:
                        _args.append(str(arg))                        

                # Boolean type
                elif type_ == 'bool':
                    value = str(arg).lower()
                    if value not in ['true', 'false']:
                        raise ValueError(f"Invalid boolean value: {arg}")
                    _args.append(value == 'true')

                # String array type
                elif type_ in STR_ARRAY_TYPES:
                    if not isinstance(arg, list):
                        raise ValueError(f"Expected list for {type_}, got {type(arg)}")
                    _args.append([str(item) for item in arg])

                # Boolean array type
                elif type_ in BOOL_ARRAY_TYPES:
                    if not isinstance(arg, list):
                        raise ValueError(f"Expected list for {type_}, got {type(arg)}")
                    _args.append([item if isinstance(item, bool) else str(item).lower() == 'true' for item in arg])

                # Bytes types
                elif type_ in BYTES_TYPES:
                    if isinstance(arg, list):
                        if len(arg) != 1:
                            raise ValueError(f"Invalid size for bytes array: {len(arg)}")
                        _args.append(self._convert_bytes(arg[0], type_))
                    else:
                        _args.append(self._convert_bytes(arg, type_))
                
                # Bytes array type
                elif type_ in BYTES_ARRAY_TYPES:
                    if not isinstance(arg, list):
                        raise ValueError(f"Expected list for {type_}, got {type(arg)}")
                    _args.append([self._convert_bytes(b, type_) for b in arg])

                # Address array type
                elif type_ == 'address[]':
                    addr_list = arg if isinstance(arg, list) else [arg]
                    formatted_addresses = []
                    
                    for addr in addr_list:
                        final_addr = self._get_agent(addr) or addr
                        if isinstance(final_addr, str):
                            if not final_addr.startswith('0x'):
                                final_addr = '0x' + final_addr
                            addr_hex = final_addr[2:].lower().zfill(40)
                            final_addr = '0x' + addr_hex
                        
                        formatted_addresses.append(final_addr)
                    
                    _args.append(formatted_addresses)

                # Integer array types
                elif type_ in INT_ARRAY_TYPES:
                    if not isinstance(arg, list):
                        raise ValueError(f"Expected list for {type_}, got {type(arg)}")
                    _args.append([int(eval(item)) if isinstance(item, str) else int(item) for item in arg])
                else:
                    raise ValueError(f"Unsupported type: {type_}")

            encoded_args = encode(types, _args)
            return encoded_args.hex()

        except Exception as e:
            logger.error(f"Exception: {str(e)}", exc_info=True)
            self._total_invalid_args += 1
            return None

    def _convert_bytes(self, value, type_name=None):
        if isinstance(value, str) and value.startswith("0x"):
            hex_value = value[2:]

            # Special handling for empty bytes
            if hex_value == "":
                return b'\x00'
                    
            if type_name and type_name.startswith("bytes") and type_name != "bytes":
                size = int(type_name[5:7])
                hex_value = hex_value.ljust(size * 2, '0')[:size * 2]
                return to_bytes(hexstr=hex_value)

            return to_bytes(hexstr=hex_value)  # for dynamic bytes

        elif isinstance(value, bytes):
            if type_name and type_name.startswith("bytes") and type_name != "bytes":
                size = int(type_name[5:7])
                if len(value) != size:
                    raise ValueError(f"Expected {size} bytes for {type_name}, got {len(value)}")
                return value

            return value  # dynamic bytes

        else:
            return bytes(str(value), 'utf-8')  # fallback for other cases

    def _inject_agents(self, json):
        json["Entities"] = self.ENTITIES

    def _get_agent(self, agent: str):
        try:
            if not isinstance(agent, str):
                logger.warning(f"Invalid agent type: {type(agent)}, expected string")
                return None
                
            if not agent.startswith("SmartianAgent"):
                return None
            
            import re
            digits_match = re.search(r'SmartianAgent(\d+)$', agent)
            if not digits_match:
                logger.warning(f"Invalid agent format: {agent}")
                return None
                
            index = int(digits_match.group(1))
            
            # Validate index range
            if not 1 <= index <= len(self.ENTITIES):
                logger.warning(f"Agent index {index} out of range [1, {len(self.ENTITIES)}], defaulting to 1")
                index = 1
                
            return self.ENTITIES[index - 1]['Contract']
            
        except (ValueError, IndexError, AttributeError) as e:
            logger.error(f"Error processing agent {agent}: {str(e)}")
            return None
        
    def _process_deploy_elements(self, tc, with_args):
        deployTx = self._get_deploy_tx(tc)
        data = ""
        if with_args and deployTx.get('Params') is not None and len(deployTx.get('Params')) > 0:
            encoded = self._encode_args("constructor", [deployTx['Params']])
            if encoded is not None:
                data = encoded
        
        return json.loads(f'''{{
            "TargetDeployer":"{str(self._get_agent(deployTx['From']) or deployTx['From'])}",
            "TargetContract":"0x6b773032d99fb9aad6fc267651c446fa7f9301af",
            "DeployTx": {{
                "From":"{str(self._get_agent(deployTx['From']) or deployTx['From'])}",
                "To":"0x6b773032d99fb9aad6fc267651c446fa7f9301af",
                "Value":"{convert_to_wei(deployTx['Value'])}",
                "Data":"{data}",
                "Timestamp":"{deployTx['Timestamp']}",
                "Blocknum":"{deployTx['Blocknum']}",
                "Function":"constructor"
            }}}}
            ''')
        
    def _process_transaction(self, tx: dict, contract_abi, with_args):
        function_name = tx['Function']
        if function_name == "" or len(function_name) == 0:
            function_name = "fallback"
            logger.info(f"converting emppty function to fallback")
        
        func_selector = self._sast_service.get_function_selector(contract_abi, function_name)
        if func_selector is None:
            logger.warning(f"Invalid function name ({function_name}), skipping transaction")
            self._total_invalid_functions += 1
            return None
        self._total_functions += 1        
        
        if function_name != "fallback":
            function_name = f"{tx['Function']}({func_selector})"

        data = func_selector # If no arguments, keep calling the function
        if with_args and tx.get('Params') is not None and len(tx.get('Params')) > 0:
            encoded = self._encode_args(func_selector, [tx['Params']])
            if encoded is not None:
                data += encoded 
        return json.loads((f'''{{
            "From":"{str(self._get_agent(tx['From']) or tx['From'])}",
            "To":"0x6b773032d99fb9aad6fc267651c446fa7f9301af",
            "Value":"{convert_to_wei(tx['Value'])}",
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
                txs.append(tx_parsed)            
        tc_json['Txs'] = txs
        return tc_json

    def get_validation_totals(self):
        return [(self._total_args, self._total_invalid_args),
                 (self._total_functions, self._total_invalid_functions)]

    def get_testcase_hash(self, fields_to_discard=None):
        fields_to_discard = fields_to_discard or set()
        filtered_data = discard_fields(self.testcase, fields_to_discard)
        
        # Use ensure_ascii=False to handle Unicode efficiently
        return hashlib.sha256(
            json.dumps(filtered_data, 
                    sort_keys=True, 
                    ensure_ascii=False).encode('utf-8')
        ).hexdigest()
