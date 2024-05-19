from openai import OpenAI
import os
import glob
import random
import json
from datetime import datetime

from genai4fuzz.services.chat import ChatService

class Genai4fuzz():

    def __init__(self) -> None:
        self._chat_service = ChatService()

    def _load_testcase():
        return
    
    def _load_abi():
        return
    
    def _is_valid_json(self, json_string: str) -> bool:
        try:
            json.loads(json_string)
            return True
        except ValueError as e:
            print(f"Invalid JSON: {e}")
            return False
    
    def _create_prompt(self, contract_abi: str, testcase_1: str, testcase_2: str) -> list: 
        testcase_format = """
            type TXData = {
                From : Address
                To: Address
                Value : UInt256
                Data : encoded calldata (length is even)
                Timestamp : int64
                Blocknum : int64
                Function : string
                OrigData : encoded calldata (length is even)
                OrigValue : bigint
            }
            type TestCase = {
                Entities: Entity list
                TargetDeployer: Address
                TargetContract: Address
                DeployTx: TXData
                Txs: TXData list
            }        
        """        
       
        return [
            {
                'role': 'user',
                'content': 'Here is the desired test case format: ' + testcase_format,
            },
            {
                'role': 'user',
                'content': 'Here is the contract ABI ' + contract_abi
            },                
            {
                'role': 'user',
                'content': '------ Example Outputs ------ Here is the #1 example seed test case file for this contract' + testcase_1,
            },
            {
                'role': 'user',
                'content': '------ Example Outputs ------ Here is the #2 example seed test case file for this contract ' + testcase_2,
            },
            {
                'role': 'user',
                'content': """
                    Your objective is to make new test cases using the same Entity list provided by the samples, and making new 
                    transaction calls (more than 6 calls) that might uncover a bug in the contract. Remeber that the Data field in TXData has a even length.
                    Do not include any explanations, only provide a RFC8259 compliant JSON response following this format without deviation.
                """
            }
        ]
        
    def run_chatgpt(self, contact_dir: str):
        
        if not os.path.exists(contact_dir):
            raise Exception("not found")
        
        base_contract_name = (os.path.basename(contact_dir.rstrip("/")))
        contract_abi_file_name = os.path.join(contact_dir, base_contract_name)  + '.abi'
        
        contract_abi_file = open(contract_abi_file_name, "r")
        contract_abi = contract_abi_file.read()
        
        testcase_file_list = [file for file in glob.glob(os.path.join(contact_dir, 'testcase_1') + '/' 'id-*')]
        testcase_1 = open(testcase_file_list[0], "r").read()
        testcase_2 = open(testcase_file_list[1], "r").read()
        
        messages = self._create_prompt(contract_abi, testcase_1, testcase_2) 
            
        chat_completion = self._chat_service.query_gpt4(messages)
        
        print("New test case generated!")        
        print(f"Is a valid JSON? {self._is_valid_json(chat_completion)}")
        print("Saving it!")
        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"gpt_testcase_new_{formatted_datetime}"
        f = open(file_name, "w")
        f.write(chat_completion)
        f.close()
    
    def run_anyscale(self, contact_dir: str, temperature: float):
        
        if not os.path.exists(contact_dir):
            raise Exception("not found")
        
        base_contract_name = (os.path.basename(contact_dir.rstrip("/")))
        contract_abi_file_name = os.path.join(contact_dir, base_contract_name)  + '.abi'
        
        contract_abi_file = open(contract_abi_file_name, "r")
        contract_abi = contract_abi_file.read()
        
        testcase_file_list = [file for file in glob.glob(os.path.join(contact_dir, 'testcase_1') + '/' 'id-*')]
        testcase_1 = open(testcase_file_list[0], "r").read()
        testcase_2 = open(testcase_file_list[1], "r").read()
        
        messages = self._create_prompt(contract_abi, testcase_1, testcase_2) 
            
        chat_completion = self._chat_service.query_anyscale(messages, temperature)
        
        print("New test case generated!")        
        print(f"Is a valid JSON? {self._is_valid_json(chat_completion)}")
        print("Saving it!")
        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"anyscale_testcase_new_{formatted_datetime}"
        f = open(file_name, "w")
        f.write(chat_completion)
        f.close()
        