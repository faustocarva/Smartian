from openai import OpenAI
import os
import glob
import random
import json
from datetime import datetime
import subprocess
from loguru import logger

from genai4fuzz.services.chat import ChatService
from genai4fuzz.services.testcase import TestCaseService

class Genai4fuzz():

    def __init__(self) -> None:
        self._chat_service = ChatService()
        self._testCase_service = TestCaseService()

    def _load_testcase(self):
        return
    
    def _load_abi(self):
        return        
        
    def validate_testcase(self, contact_dir: str, testcase: str):
        if not os.path.exists(contact_dir):
            raise Exception("not found")
        
        base_contract_name = (os.path.basename(contact_dir.rstrip("/")))
        contract_abi_file_name = os.path.join(contact_dir, base_contract_name)  + '.abi'
        contract_abi_file = open(contract_abi_file_name, "r")
        contract_abi = contract_abi_file.read()
        
        self._testCase_service.validateTestCaseTxs(testcase, contract_abi)
        return
        
    def run_smartian(self, testcase: str, program: str):
        fsharp_executable = '../build/Smartian.dll'
        parameters = [f'replay -p {program} -i {testcase}']
        cmd = " ".join(['dotnet', fsharp_executable] + parameters)
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        print(result.stdout)
        print(result.stderr)
    
    def _create_prompt(self, contract_abi: str, testcase_1: str, testcase_2: str) -> list: 
        testcase_format = """
            type Entity = {
                Balance: UInt256
                Account: Address
                Agent: AgentType
                Contract: Address
            }        
            type TXData = {
                From : Entity Contract Address
                To: Address
                Value : UInt256
                Data : Keccak (SHA-3) hash of the calldata (length is even)
                Timestamp : int64
                Blocknum : int64
            }
            type TestCase = {
                Entities: Entity list
                TargetDeployer: Address
                TargetContract: Address
                DeployTx: TXData
                Txs: TXData list
            }        
        """        
        functions_descs = self._testCase_service.getFunctionsFromABI(contract_abi)       
        functions_descs_str = '\n'.join([function for function in functions_descs])
        
        return [
            {
                'role': 'user',
                'content': 'Here is the desired test case format: ' + testcase_format,
            },
            {
                'role': 'user',
                'content': 'Here is the Solidity contract functions to use in the test case generation: ' + functions_descs_str
            },
            {
                'role': 'user',            
                'content': """            
                    Here are the TXData Data calldata encoding rules in brief:

                    Function Selector: 4 bytes (keccak-256 hash of function name and parameter types)
                    Parameter packing:
                        Static types (address, uint, bool): padded to 32 bytes
                        Dynamic types (string, bytes, arrays): length (32 bytes) + data
                    ABI encoding: recursive encoding of parameters, following the above rules
                    Padded to 32 bytes: each parameter is padded to 32 bytes with zeros
                    The length of a calldata value is always a multiple of 32 bytes, since each parameter is padded to 32 bytes.
                    So, the length of a calldata value is always an even number of bytes.                                
                    """            
            },
            # {
            #     'role': 'user',
            #     'content': 'To generate Data in TXData: The first four bytes of the call data for a function call specifies the function to be called. It is the first (left, high-order in big-endian) four bytes of the Keccak (SHA-3) hash of the signature of the function. The signature is defined as the canonical expression of the basic prototype, i.e. the function name with the parenthesised list of parameter types. Parameter types are split by a single comma - no spaces are used'
            # },            
            {
                'role': 'user',
                'content': '------ Example Outputs ------ Here is the #1 example seed test case file for this contract' + testcase_1,
            },
            # {
            #     'role': 'user',
            #     'content': '------ Example Outputs ------ Here is the #2 example seed test case file for this contract ' + testcase_2,
            # },
            {
                'role': 'user',
                'content': """
                    Your objective is to make new test cases using the same Entity list provided by the samples, and making new 
                    transaction calls (more than 5 calls) with complete valid calldata encoding, that might uncover a bug in the contract. 
                    Do not include any explanations, only provide a RFC8259 compliant JSON response following this format without deviation.
                """
            }
        ]
        
    def run_chatgpt(self, contact_dir: str):
        
        if not os.path.exists(contact_dir):
            raise Exception("not found")
        
        base_contract_name = (os.path.basename(contact_dir.rstrip("/")))
        contract_abi_file_name = os.path.join(contact_dir, base_contract_name)  + '.abi'
        contract_bin_file_name = os.path.join(contact_dir, base_contract_name)  + '.bin'        
        contract_abi_file = open(contract_abi_file_name, "r")
        contract_abi = contract_abi_file.read()
        
        testcase_file_list = [file for file in glob.glob(os.path.join(contact_dir, 'testcase_1') + '/' 'id-*')]
        testcase_1 = open(testcase_file_list[0], "r").read()
        testcase_2 = open(testcase_file_list[1], "r").read()
        
        messages = self._create_prompt(contract_abi, testcase_1, testcase_2) 
            
        chat_completion = self._chat_service.query_gpt4(messages)
        
        print("New test case generated!")        
        print(f"Is a valid JSON? {self._testCase_service.is_valid_json(chat_completion)}")
        print("Saving it!")
        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"gpt_testcase_new_{formatted_datetime}"
        f = open(file_name, "w")
        f.write(chat_completion)
        f.close()
        self.run_smartian(file_name, contract_bin_file_name)        
    
    def run_anyscale(self, contact_dir: str, temperature: float):
        
        if not os.path.exists(contact_dir):
            raise Exception("not found")
        
        base_contract_name = (os.path.basename(contact_dir.rstrip("/")))
        contract_abi_file_name = os.path.join(contact_dir, base_contract_name)  + '.abi'
        contract_bin_file_name = os.path.join(contact_dir, base_contract_name)  + '.bin'
        
        contract_abi_file = open(contract_abi_file_name, "r")
        contract_abi = contract_abi_file.read()
        
        # testcase_file_list = [file for file in glob.glob(os.path.join(contact_dir, 'testcase_1') + '/' 'id-*')]
        # testcase_1 = open(testcase_file_list[0], "r").read()
        # testcase_2 = open(testcase_file_list[1], "r").read()
        
        # testcase_file_list = [file for file in glob.glob(contact_dir + '/' 'example')]
        testcase_1 = open(os.path.join(contact_dir, 'example'), "r").read()

        messages = self._create_prompt(contract_abi, testcase_1, testcase_1) 
            
        chat_completion = self._chat_service.query_anyscale(messages, temperature)
        
        print("New test case generated!")        
        print(f"Is a valid JSON? {self._testCase_service.is_valid_json(chat_completion)}")
        print("Saving it!")
        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"anyscale_testcase_new_{formatted_datetime}"
        f = open(file_name, "w")
        f.write(chat_completion)
        f.close()
        self.run_smartian(file_name, contract_bin_file_name)