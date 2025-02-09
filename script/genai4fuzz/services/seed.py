import json
import copy
import hashlib
from typing import List, Any, Dict, Optional, Union
from dataclasses import dataclass
from eth_abi import encode
from eth_utils import to_bytes
from loguru import logger
from pydantic import ValidationError

from genai4fuzz.model.testcase import TestCaseModel
from genai4fuzz.utils.general import flatten_list, discard_fields
from genai4fuzz.config import Config
from genai4fuzz.services.sast import SastService

@dataclass
class ContractEntity:
    """Represents a contract entity with balance, account, agent and contract details."""
    balance: str
    account: str
    agent: str
    contract: str

class Seed:
    """
    Handles test case processing and validation for smart contract interactions.
    
    This class processes test cases, validates their structure, and handles
    the encoding of arguments for contract interactions.
    """
    
    # Define entities as a tuple of immutable ContractEntity objects
    __ENTITIES = tuple([
        ContractEntity(
            balance="10000000000000000000000",
            account="0xb7705ae4c6f81b66cdb323c65f4e8133690fc099",
            agent="SmartianAgent",
            contract="0x24cd2edba056b7c654a50e8201b619d4f624fdda"
        ),
        ContractEntity(
            balance="10000000000000000000000",
            account="0x00120000000000000000000000000000000001d2",
            agent="SmartianAgent",
            contract="0x118a2c24808934116e6ab4c00ff48145d23b09e1"
        ),
        ContractEntity(
            balance="10000000000000000000000",
            account="0x001200000000000000000000000000000000021c",
            agent="SmartianAgent",
            contract="0x226cc61b3eac93cc2cc9d6cb8d61856670d50fad"
        ),
        ContractEntity(
            balance="10000000000000000000000",
            account="0x0012000000000000000000000000000000000229",
            agent="SmartianAgent",
            contract="0x33b808a5ae24c410e8739b5ca2d5ef3931d3e09f"
        )
    ])

    # Configuration constants
    DEFAULT_CONTRACT_ADDRESS = "0x6b773032d99fb9aad6fc267651c446fa7f9301af"
    DEFAULT_BLOCK_NUMBER = "20000944"
    
    def __init__(self, tc: Dict[str, Any]) -> None:
        """
        Initialize TestCase with the provided test case dictionary.
        
        Args:
            tc: Dictionary containing the test case data
        """
        self._config = Config()
        self._sast_service = SastService()
        self.testcase = tc
        self.interfaces: Dict[str, Any] = {}
        
        # Initialize counters
        self._stats = {
            'total_args': 0,
            'invalid_args': 0,
            'total_functions': 0,
            'invalid_functions': 0
        }
        
        # Validate structure
        self._is_valid_struct = self.is_valid_testcase_struct()
        if not self._is_valid_struct:
            logger.error("TestCase struct does not respect JSON format or invalid data types")

    @staticmethod
    def try_to_adapt_json_testcase(data: Union[Dict[str, Any], List[Any], None]) -> Dict[str, Any]:
        """
        Adapt input data to a consistent test case format.
        
        Args:
            data: Input data that could be a dictionary or list
            
        Returns:
            Dictionary containing the processed test case data
        """
        if data is None:
            return {}
        if isinstance(data, dict):
            return data.get('TestCases', {}) or data.get('TestCase', {})
        return data if isinstance(data, dict) else {}

    @property
    def entities(self) -> List[Dict[str, str]]:
        """Return a deep copy of the entities configuration."""
        return [dataclasses.asdict(entity) for entity in self.__ENTITIES]

    def _convert_bytes(self, value: str) -> bytes:
        """
        Convert a string value to bytes.
        
        Args:
            value: String value to convert
            
        Returns:
            Converted bytes value
        """
        if value.startswith("0x"):
            padded_string = value[2:].ljust(32, '0')[:32]
            return to_bytes(hexstr=padded_string)
        return bytes(value, 'utf-8')

    def _encode_args(self, function_selector: str, tx: List[Any]) -> Optional[str]:
        """
        Encode function arguments for contract interaction.
        
        Args:
            function_selector: The function selector string
            tx: List of arguments to encode
            
        Returns:
            Encoded arguments as hex string or None if encoding fails
            
        Raises:
            ValueError: If argument encoding fails due to invalid input
        """
        try:
            int_types = {"uint8", "uint16", "uint32", "uint64", "uint128", "uint256",
                        "int8", "int16", "int32", "int64", "int128", "int256"}
            int_array_types = {t + "[]" for t in int_types}
            str_types = {'address', 'string'}
            
            func, types = self.interfaces[function_selector]
            logger.info(f"Processing function {func} with types {types} and args {tx}")
            
            args = flatten_list(tx) if not any(t.endswith('[]') for t in types) and any(isinstance(i, list) for i in tx) else tx
            processed_args = []
            
            for i, (arg_type, arg_value) in enumerate(zip(types, args)):
                processed_args.append(self._process_argument(arg_type, arg_value, int_types, str_types, int_array_types))
            
            encoded_args = encode(types, processed_args)
            self._stats['total_args'] += 1
            return encoded_args.hex()
            
        except Exception as e:
            logger.error(f"Argument encoding failed: {str(e)}")
            self._stats['invalid_args'] += 1
            raise ValueError(f"Failed to encode arguments: {str(e)}")

    def _process_argument(self, arg_type: str, arg_value: Any, int_types: set, str_types: set, int_array_types: set) -> Any:
        """Process a single argument based on its type."""
        if arg_type in int_types:
            return int(arg_value)
        elif arg_type in str_types:
            if arg_type == "address":
                return str(self._resolve_agent(arg_value) or arg_value)
            return str(arg_value)
        elif arg_type == 'bool':
            return self._process_boolean(arg_value)
        elif arg_type in ('bytes32[]', 'bytes32', 'bytes'):
            return self._process_bytes(arg_type, arg_value)
        elif arg_type == 'address[]':
            return self._process_address_array(arg_value)
        elif arg_type in int_array_types:
            return [int(item) for item in arg_value]
        raise ValueError(f"Unsupported argument type: {arg_type}")

    def _process_boolean(self, value: Any) -> bool:
        """Process and validate boolean values."""
        str_value = str(value).lower()
        if str_value not in ('true', 'false'):
            raise ValueError(f"Invalid boolean value: {value}")
        return str_value == 'true'

    def _process_bytes(self, arg_type: str, value: Any) -> Union[bytes, List[bytes]]:
        """Process and validate bytes values."""
        if arg_type == 'bytes32[]':
            if not isinstance(value, list):
                raise ValueError("Expected list of bytes")
            return [self._convert_bytes(b) for b in value]
        
        if isinstance(value, list):
            if len(value) > 1:
                raise ValueError("Invalid size for bytes value")
            return self._convert_bytes(value[0])
        return self._convert_bytes(value)

    def _process_address_array(self, addresses: List[str]) -> List[str]:
        """Process and validate address arrays."""
        if not isinstance(addresses, list):
            raise ValueError("Expected list of addresses")
        return [str(self._resolve_agent(addr) or addr) for addr in addresses]

    def _resolve_agent(self, agent: str) -> Optional[str]:
        """
        Resolve an agent identifier to its contract address.
        
        Args:
            agent: Agent identifier string
            
        Returns:
            Contract address or None if agent cannot be resolved
        """
        try:
            index = int(agent[-1])
            if 1 <= index <= len(self.__ENTITIES):
                return self.__ENTITIES[index - 1].contract
            logger.warning(f"Invalid agent index: {index}")
            return None
        except (ValueError, IndexError):
            return None

    def _get_agent(self, agent: str) -> str:
        """
        Get an agent's contract address with fallback to first agent.
        
        Args:
            agent: Agent identifier string
            
        Returns:
            Contract address
        """
        try:
            index = int(agent[-1])
            if not 1 <= index <= len(self.__ENTITIES):
                logger.warning("Invalid SmartianAgent id, defaulting to 1")
                index = 1
            return self.__ENTITIES[index - 1].contract
        except (ValueError, IndexError):
            logger.warning("Failed to parse agent ID, defaulting to first agent")
            return self.__ENTITIES[0].contract

    def process_testcase(self, contract_abi: Dict[str, Any], with_args: bool) -> Optional[Dict[str, Any]]:
        """
        Process the test case with the provided contract ABI.
        
        Args:
            contract_abi: Contract ABI dictionary
            with_args: Whether to include encoded arguments
            
        Returns:
            Processed test case dictionary or None if invalid
        """
        if not self._is_valid_struct:
            return None
            
        self.interfaces = self._sast_service.get_interface_from_abi(contract_abi)
        
        # Build test case JSON structure
        tc_json = {
            "Entities": self.entities,
            **self._build_deploy_transaction(with_args),
            "Txs": self._build_transactions(contract_abi, with_args)
        }
        
        return tc_json

    def _build_deploy_transaction(self, with_args: bool) -> Dict[str, Any]:
        """Build the deployment transaction section of the test case."""
        deploy_tx = self._get_deploy_tx(self.testcase)
        data = ""
        
        if with_args and deploy_tx.get('Params'):
            try:
                data = self._encode_args("constructor", deploy_tx['Params'])
            except ValueError as e:
                logger.error(f"Failed to encode constructor arguments: {e}")

        return {
            "TargetDeployer": self._get_agent(deploy_tx['From']),
            "TargetContract": self.DEFAULT_CONTRACT_ADDRESS,
            "DeployTx": {
                "From": self._get_agent(deploy_tx['From']),
                "To": self.DEFAULT_CONTRACT_ADDRESS,
                "Value": deploy_tx['Value'],
                "Data": data or "",
                "Timestamp": deploy_tx['Timestamp'],
                "Blocknum": deploy_tx['Blocknum'],
                "Function": "constructor"
            }
        }

    def _build_transactions(self, contract_abi: Dict[str, Any], with_args: bool) -> List[Dict[str, Any]]:
        """Build the transactions section of the test case."""
        transactions = []
        
        for tx in self._get_txs(self.testcase):
            processed_tx = self._process_transaction(tx, contract_abi, with_args)
            if processed_tx:
                transactions.append(processed_tx)
                
        return transactions

    def _process_transaction(self, tx: Dict[str, Any], contract_abi: Dict[str, Any], with_args: bool) -> Optional[Dict[str, Any]]:
        """Process a single transaction in the test case."""
        function_name = tx['Function']
        func_selector = self._sast_service.get_function_selector(contract_abi, function_name)
        
        if func_selector is None:
            logger.warning(f"Invalid function name ({function_name}), skipping transaction")
            self._stats['invalid_functions'] += 1
            return None
            
        self._stats['total_functions'] += 1
        
        # Build function identifier
        if function_name in ("fallback", "fallback()"):
            function_id = function_name
        else:
            function_id = f"{function_name}({func_selector})"
            
        # Process transaction data
        data = func_selector
        if with_args and tx.get('Params'):
            try:
                encoded = self._encode_args(func_selector, tx['Params'])
                if encoded:
                    data += encoded
            except ValueError as e:
                logger.error(f"Failed to encode transaction arguments: {e}")
                
        return {
            "From": self._get_agent(tx['From']),
            "To": self.DEFAULT_CONTRACT_ADDRESS,
            "Value": tx['Value'],
            "Data": data,
            "Timestamp": tx['Timestamp'],
            "Blocknum": tx.get('Blocknum', self.DEFAULT_BLOCK_NUMBER),
            "Function": function_id
        }

    def is_valid_testcase_struct(self) -> bool:
        """Validate the test case structure using Pydantic model."""
        try:
            testcase_data = self.testcase.get("TestCase", self.testcase)
            TestCaseModel(**testcase_data)
            return True
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return False

    def get_testcase_hash(self, fields_to_discard: List[str] = None) -> str:
        """
        Generate a hash of the test case, optionally excluding specified fields.
        
        Args:
            fields_to_discard: List of field names to exclude from hash calculation
            
        Returns:
            SHA-256 hash of the processed test case
        """
        filtered_data = discard_fields(self.testcase, fields_to_discard or [])
        obj_str = json.dumps(filtered_data, sort_keys=True)
        return hashlib.sha256(obj_str.encode('utf-8')).hexdigest()

    def get_validation_totals(self) -> List[tuple]:
        """Return the validation statistics as tuples."""
        return [
            (self._stats['total_args'], self._stats['invalid_args']),
            (self._stats['total_functions'], self._stats['invalid_functions'])
        ]