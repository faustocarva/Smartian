from openai import OpenAI
import os
import glob
import shutil
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
        
    def _read_contract_files(self, contact_dir):
        base_contract_name = (os.path.basename(contact_dir.rstrip("/")))
        contract_abi_file_name = os.path.join(contact_dir, base_contract_name)  + '.abi'
        contract_bin_file_name = os.path.join(contact_dir, base_contract_name)  + '.bin'
        
        contract_abi_file = open(contract_abi_file_name, "r")
        contract_abi = contract_abi_file.read()
        return contract_bin_file_name, contract_abi, base_contract_name
        
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
    
    def _create_prompt(self, contract_abi: str, testcase: list) -> list: 
        
        functions_descs = self._testCase_service.getFunctionsFromABI(contract_abi, False)
        functions_descs_str = '\n'.join([function for function in functions_descs])
        
        prompt =  [
            {
                'role': 'system',
                'content':  """
                    You are an expert assistant specializing in generating EVM test cases with a deep understanding of Solidity and Ethereum bugs and vulnerabilities. 
                    Respond strictly in JSON format, following the provided instructions without any additional text.                
                """
            },
            {
                'role': 'user',            
                'content': '\nYou have four sender contracts: SmartianAgent1, SmartianAgent2, SmartianAgent3, and SmartianAgent4. Use their names in the From fields as needed.'
            },
            {
                'role': 'user',
                'content':'\n**Solidity Contract Functions for Test Case Generation:** \n' + functions_descs_str
            },            
            {
                'role': 'user',
                'content': """
                    ### JSON Grammar for EVM Test Case

                    #### Root
                    - An array of `TestCase` objects.

                    #### TestCase
                    - **DeployTx**: An object representing the deployment transaction.
                    - **Txs**: An array of transaction (`Tx`) objects.

                    #### DeployTx
                    - **From**: A string representing the sender's name.
                    - **Value**: A string representing the amount of Ether sent with the transaction.
                    - **Timestamp**: A string representing the timestamp of the transaction.
                    - **Blocknum**: A string representing the block number when the transaction was included.

                    #### Tx (Transaction)
                    - **From**: A string representing the sender's name.
                    - **Value**: A string representing the amount of Ether sent with the transaction.
                    - **Function**: A string representing the function name being called.
                    - **Params** (optional): An array representing the parameters passed to the function.
                    - Parameters can be nested arrays.
                    - **Timestamp**: A string representing the timestamp of the transaction.
                    - **Blocknum**: A string representing the block number when the transaction was included.
                    
                    ### Example                    
                """
            },
            {
                'role': 'user',
                'content': '\n### Example \n' + testcase[0]
            },
            {
                'role': 'user',
                'content': """
                    ### Notes
                    - Each `TestCase` contains a `DeployTx` object and an array of `Tx` objects.
                    - Each transaction (`Tx`) includes details such as sender (`From`), value (`Value`), function name (`Function`), optional parameters (`Params`), timestamp (`Timestamp`), and block number (`Blocknum`).
                    - Parameters (`Params`) can be nested arrays to accommodate functions requiring multiple lists of parameters.
                
                    **Objective:** Create 10 new test case objects, each containing more than 4 transactions that might uncover bugs in the contract. 
                    Ensure the transactions use raw values and respect the data types in the function signatures. 
                    Provide the response as RFC8259 compliant JSON without explanations.
                """
            }
        ]
        
        return prompt

    def estimate_prompt(self, contact_dir: str, model: str):
        if not os.path.exists(contact_dir):
            raise Exception("not found")
        
        _, contract_abi, _ = self._read_contract_files(contact_dir)
        testcase = open('example.json', "r").read()
        
        messages = self._create_prompt(contract_abi, [testcase])
        print (f"Total tokens from prompt: {self._chat_service.count_tokens(messages, model)}")
   
    def dump_prompt(self, contact_dir: str):
        if not os.path.exists(contact_dir):
            raise Exception("not found")
        
        _, contract_abi, _ = self._read_contract_files(contact_dir)
        testcase = open('example.json', "r").read()
                
        messages = self._create_prompt(contract_abi, [testcase])        
        print (self._chat_service.dump_prompt(messages))

    def run_gpt(self, contact_dir: str, model: str, temperature: float):
        self.run_llm(contact_dir, "gpt", model, temperature)

    def run_anyscale(self, contact_dir: str, model: str, temperature: float):        
        self.run_llm(contact_dir, "anyscale", model, temperature)
        
    def run_llm(self, contact_dir: str, llm: str, model: str, temperature: float):
        
        if not os.path.exists(contact_dir):
            raise Exception("not found")
        
        contract_bin_file_name, contract_abi, base_contract_name = self._read_contract_files(contact_dir)
        testcase = open('example.json', "r").read()        
        
        messages = self._create_prompt(contract_abi, [testcase]) 

        if llm == "gpt":
            logger.info(f"Requesting test cases for contract {base_contract_name}")            
            chat_completion = self._chat_service.query_gpt4(messages, model, temperature)
        elif llm == "anyscale": 
            chat_completion = self._chat_service.query_anyscale(messages, model, temperature)
            
        logger.info(f"New {llm} test case generated!")
        logger.info(f"Is a valid JSON? {self._testCase_service.is_valid_json(chat_completion)}")
                
        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")
        
        testcase_file_name = f"{base_contract_name}_{llm}_{model}_{temperature}T_testcase_{formatted_datetime}"
        f = open(os.path.join(contact_dir, testcase_file_name), "w")
        f.write(chat_completion)
        f.close()
        
        prompt_file_name = os.path.join(contact_dir, f"{base_contract_name}_{llm}_{model}_{temperature}T_prompt_{formatted_datetime}")        
        self._chat_service.dump_save_prompt(messages, prompt_file_name)

        logger.info(f"Prompt tokens: {chat_completion.usage.prompt_tokens}, Completition tokens {chat_completion.usage.completion_tokens}")
        logger.info(f"Saving test case {testcase_file_name} and prompt {prompt_file_name}!")
    
    def convert_to_smartian(self, contract_dir: str, output_dir: str, model=""):
        if not os.path.isdir(contract_dir):
            return
        if (model is None):
            model = ""
        if (output_dir is None):
            output_dir = contract_dir
            
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)
        os.makedirs(output_dir)
                        
        _, contract_abi, base_contract_name = self._read_contract_files(contract_dir)
        
        file_list = [file for file in glob.glob(os.path.join(contract_dir, '')+f"*{model}*_testcase_*")]
        file_index = 0
        for file_path in file_list:
            # try:
                with open(file_path, 'r') as file:
                    content = file.read()
                    if not self._testCase_service.is_valid_json(content):
                        content = self._testCase_service.json_from_text(content)
                        if not self._testCase_service.is_valid_json(content):
                            raise ValueError("TestCase cant be loaded as JSON")
                    tcs = json.loads(content)
                    tc_index = 0
                    for tc in tcs:
                        if not self._testCase_service.validateTestCaseStruct(tc):
                            raise ValueError("TestCase struct does not respect JSON format")
                        tc_json = self._testCase_service.processTestCase(tc, contract_abi)
                        testcase_file_name = f"id-{file_index:05}_{tc_index:05}"
                        with open(os.path.join(output_dir, testcase_file_name), "w") as f:
                            f.write(json.dumps(tc_json, indent=4))                        
                        tc_index += 1        
                        #print(json.dumps(tc_json, indent=4))
                file_index += 1                        
            # except Exception as e:
            #     logger.error(f"Exeption {e}, file {file_path}")
            #     continue
