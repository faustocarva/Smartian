import pytest
from unittest.mock import Mock, patch
import json
from eth_abi import encode
from eth_utils import to_bytes
from pydantic import ValidationError

from genai4fuzz.model.testcase import TestCaseModel, DeployTx, Tx
from genai4fuzz.services.testcase import TestCase

@pytest.fixture
def valid_testcase():
    return {
        "TestCase": {
            "DeployTx": {
                "From": "SmartianAgent1",
                "Value": "0",
                "Function": "constructor",
                "Timestamp": "1234567890",
                "Blocknum": "12345",
                "Params": ["1000", "0xaddress"]
            },
            "Txs": [
                {
                    "From": "SmartianAgent1",
                    "Value": "100",
                    "Function": "transfer",
                    "Timestamp": "1234567891",
                    "Blocknum": "12346",
                    "Params": ["0xrecipient", "1000"]
                }
            ]
        }
    }

@pytest.fixture
def invalid_testcase():
    return {
        "TestCase": {
            "DeployTx": {
                "From": "SmartianAgent1",
                "Value": "-1",  # Invalid: negative value
                "Function": "constructor",
                "Timestamp": "1234567890",
                "Blocknum": "12345"
            },
            "Txs": []
        }
    }

@pytest.fixture
def sample_contract_abi():
    return [
        {
            "inputs": [
                {"type": "uint256"},
                {"type": "address"}
            ],
            "stateMutability": "nonpayable",
            "type": "constructor"
        },
        {
            "inputs": [
                {"type": "address", "name": "recipient"},
                {"type": "uint256", "name": "amount"}
            ],
            "name": "transfer",
            "outputs": [{"type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]

def test_valid_testcase_model(valid_testcase):
    tc = TestCase(valid_testcase)
    assert tc._is_valid_struct == True
    
    # Verify the Pydantic model validation works
    testcase_data = valid_testcase["TestCase"]
    model = TestCaseModel(**testcase_data)
    assert isinstance(model.DeployTx, DeployTx)
    assert isinstance(model.Txs[0], Tx)

def test_invalid_testcase_model(invalid_testcase):
    tc = TestCase(invalid_testcase)
    assert tc._is_valid_struct == False
    
    # Verify the Pydantic validation catches the error
    with pytest.raises(ValidationError):
        testcase_data = invalid_testcase["TestCase"]
        TestCaseModel(**testcase_data)

def test_deploy_tx_validation():
    # Test valid deploy tx
    valid_deploy = {
        "From": "SmartianAgent1",
        "Value": "0",
        "Function": "constructor",
        "Timestamp": "1234567890",
        "Blocknum": "12345"
    }
    deploy_tx = DeployTx(**valid_deploy)
    assert deploy_tx.From == "SmartianAgent1"
    assert deploy_tx.Value == 0
    
    # Test invalid deploy tx (negative value)
    invalid_deploy = valid_deploy.copy()
    invalid_deploy["Value"] = "-1"
    with pytest.raises(ValidationError):
        DeployTx(**invalid_deploy)

def test_tx_validation():
    # Test valid transaction
    valid_tx = {
        "From": "SmartianAgent1",
        "Value": "100",
        "Function": "transfer",
        "Timestamp": "1234567891",
        "Blocknum": "12346",
        "Params": ["0xrecipient", "1000"]
    }
    tx = Tx(**valid_tx)
    assert tx.From == "SmartianAgent1"
    assert tx.Value == 100
    assert tx.Params == ["0xrecipient", "1000"]
    
    # Test invalid transaction (value too large)
    invalid_tx = valid_tx.copy()
    invalid_tx["Value"] = str(2**256)  # One more than maximum allowed
    with pytest.raises(ValidationError):
        Tx(**invalid_tx)

def test_get_testcase_hash(valid_testcase):
    tc = TestCase(valid_testcase)
    hash1 = tc.get_testcase_hash()
    hash2 = tc.get_testcase_hash()
    assert hash1 == hash2

def test_get_testcase_hash_with_fields_to_discard(valid_testcase):
    tc = TestCase(valid_testcase)
    hash1 = tc.get_testcase_hash()
    hash2 = tc.get_testcase_hash(fields_to_discard={"Timestamp"})
    assert hash1 != hash2

def test_get_agent_valid():
    tc = TestCase({})
    agent = tc._get_agent("SmartianAgent1")
    assert agent == "0x24cd2edba056b7c654a50e8201b619d4f624fdda"

def test_get_agent():
    tc = TestCase({})
    # Test non-SmartianAgent string - should return None
    assert tc._get_agent("OtherAgent") is None
    
    # Test invalid SmartianAgent index - should default to index 1
    assert tc._get_agent("SmartianAgent5") == "0x24cd2edba056b7c654a50e8201b619d4f624fdda"
    
    # Test valid SmartianAgent
    assert tc._get_agent("SmartianAgent1") == "0x24cd2edba056b7c654a50e8201b619d4f624fdda"
    assert tc._get_agent("SmartianAgent2") == "0x118a2c24808934116e6ab4c00ff48145d23b09e1"

@pytest.mark.parametrize("value", [
    "0x1234",
    "test"
])

def test_convert_bytes(value):
    tc = TestCase({})
    result = tc._convert_bytes(value)
    if value.startswith("0x"):
        # For hex values, check it contains the hex value
        padded_hex = value[2:].ljust(32, '0')[:32]
        expected = to_bytes(hexstr=padded_hex)
        assert result == expected
    else:
        # For string values, check it contains the string as bytes
        expected = bytes(value, 'utf-8')
        assert result == expected

@patch('genai4fuzz.services.sast.SastService')
def test_process_testcase(mock_sast, valid_testcase, sample_contract_abi):
    # Convert contract_abi to string as expected by the implementation
    contract_abi_str = json.dumps(sample_contract_abi)
    
    # Setup mock
    mock_sast_instance = Mock()
    mock_sast_instance.get_function_selector.return_value = "a9059cbb"  # Without 0x prefix
    mock_sast_instance.get_interface_from_abi.return_value = {
        "a9059cbb": ("transfer", ["address", "uint256"])
    }
    mock_sast.return_value = mock_sast_instance

    tc = TestCase(valid_testcase)
    result = tc.process_testcase(contract_abi_str, True)

    assert result is not None
    assert "TargetDeployer" in result
    assert "DeployTx" in result
    assert "Txs" in result
    assert len(result["Txs"]) == 1
    assert result["Txs"][0]["Function"] == "transfer(a9059cbb)"  # Without 0x prefix

def test_process_testcase_with_invalid_function(valid_testcase, sample_contract_abi):
    tc = TestCase(valid_testcase)
    tc.testcase["TestCase"]["Txs"][0]["Function"] = "invalidFunction"
    
    # Convert contract_abi to string
    contract_abi_str = json.dumps(sample_contract_abi)
    
    with patch('genai4fuzz.services.sast.SastService') as mock_sast:
        mock_sast_instance = Mock()
        mock_sast_instance.get_function_selector.return_value = None
        mock_sast_instance.get_interface_from_abi.return_value = {}
        mock_sast.return_value = mock_sast_instance
        
        result = tc.process_testcase(contract_abi_str, True)
        
        assert result is not None
        assert len(result["Txs"]) == 0  # Invalid function should be skipped

def test_validation_totals(valid_testcase, sample_contract_abi):
    tc = TestCase(valid_testcase)
    # Convert contract_abi to string
    contract_abi_str = json.dumps(sample_contract_abi)
    tc.process_testcase(contract_abi_str, True)
    args_total, funcs_total = tc.get_validation_totals()
    
    assert isinstance(args_total, tuple)
    assert isinstance(funcs_total, tuple)
    assert len(args_total) == 2  # (total_args, invalid_args)
    assert len(funcs_total) == 2  # (total_functions, invalid_functions)

def test_encode_args_with_various_types():
    tc = TestCase({})
    tc.interfaces = {
        "test_selector": ("test_function", ["uint256", "address", "bool", "bytes32"])
    }
    
    args = [
        "1000",
        "0x1234567890123456789012345678901234567890",
        "true",
        "0x1234567890123456789012345678901234567890123456789012345678901234"
    ]
    
    result = tc._encode_args("test_selector", args)
    assert result is not None
    assert isinstance(result, str)
    assert not result.startswith("0x")  # The method returns hex without 0x prefix