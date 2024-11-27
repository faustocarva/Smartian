import os
import glob
import shutil
import json
import subprocess
import tempfile
import re
from collections import defaultdict
from loguru import logger
from datetime import datetime

from genai4fuzz.utils.general import is_valid_json, json_from_text, get_pcs_and_jumpis
from genai4fuzz.services.chat import ChatService
from genai4fuzz.services.testcase import TestCase
from genai4fuzz.services.sast import SastService

class Genai4fuzz():

    def __init__(self) -> None:
        self._chat_service = ChatService()
        self._sast_service = SastService()
            
    def _read_contract_files(self, contact_dir):
        base_contract_name = (os.path.basename(contact_dir.rstrip("/")))
        contract_abi_file_name = os.path.join(contact_dir, base_contract_name)  + '.abi'
        contract_bin_file_name = os.path.join(contact_dir, base_contract_name)  + '.bin'
        contract_sol_file_name = os.path.join(contact_dir, base_contract_name)  + '.sol'
        
        contract_abi_file = open(contract_abi_file_name, "r")
        contract_abi = contract_abi_file.read()
        return contract_bin_file_name, contract_abi, base_contract_name, contract_sol_file_name
        
    def _extract_deepest_name(self, path):
        deepest_name = os.path.basename(path)
        if not deepest_name:
            return os.path.basename(os.path.dirname(path))
    
        return deepest_name
    
    def run_smartian(self, program: str, testcase: str):
        fsharp_executable = '../build/Smartian.dll'
        parameters = [f'replay --csvout  -p {program} -i {testcase}']
        cmd = " ".join(['dotnet', fsharp_executable] + parameters)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return result.stdout
    
    def _create_prompt(self, contract_abi: str, contract_sol: str, testcase: list, total_tests=10, total_txs=4) -> list: 
        
        functions_descs = self._sast_service.get_functions_from_ABI(contract_abi)
        functions_with_modifiers = self._sast_service.get_function_modifiers(contract_sol, functions_descs)
        if functions_with_modifiers is not None:
            functions_descs_str = '\n'.join([function for function in functions_with_modifiers])
        else:
            functions_descs_str = '\n'.join([function for function in functions_descs])
        
        prompt =  [
            {
                'role': 'system',
                'content':  """
                    You are an expert assistant specializing in Solidity fuzzing with a deep understanding of SWC and DASP vulnerabilities. 
                    Your objective is to generate a diverse set of transactions and inputs targeting the main EVM/Solidity vulnerabilities.
                    Respond strictly in JSON format, following the provided instructions without any additional text.
                """
            },
            {
                'role': 'user',            
                'content': '\n### You have four sender contracts: SmartianAgent1, SmartianAgent2, SmartianAgent3, and SmartianAgent4. Use their names in the parameters that need an address and in From fields as needed.'
            },
            {
                'role': 'user',
                'content':'\n### You have the following Solidity Contract Functions for Test Case Generation: \n' + functions_descs_str
            },            
            {
                'role': 'user',
                'content': """
                    ### JSON Grammar for EVM Test Case

                    #### Root
                    - An array of `TestCase` objects.

                    #### TestCase
                    - **DeployTx**: An object representing the deployment transaction, using the constructor function.
                    - **Txs**: An array of transaction (`Tx`) objects.

                    #### DeployTx
                    - **From**: A string representing the deployer's name or address.
                    - **Value**: A string representing the amount of Ether sent with the transaction.
                    - **Function**: A string representing the constructor function name being called.                    
                    - **Params** (optional): An array representing the parameters passed to the constructor, if it exists.                    
                    - **Timestamp**: A string representing the timestamp of the transaction.
                    - **Blocknum**: A string representing the block number when the transaction was included.

                    #### Tx (Transaction)
                    - **From**: A string representing the sender's name.
                    - **Value**: A string representing the amount of Ether sent with the transaction, if function is payable.
                    - **Function**: A string representing the function name being called.
                    - **Params** (optional): An array representing the parameters passed to the function.
                    - Parameters can be nested arrays.
                    - **Timestamp**: A string representing the timestamp of the transaction.
                    - **Blocknum**: A string representing the block number when the transaction was included.
                """
            },
            {
                'role': 'user',
                'content': '\n### Example \n' + testcase[0]
            },
            {
                'role': 'user',
                'content': f'''
                    ### Notes
                    - Each `TestCase` contains a `DeployTx` object and an array of `Tx` objects.
                    - Each transaction (`Tx`) includes details such as sender (`From`), value (`Value`), function name (`Function`), optional parameters (`Params`), timestamp (`Timestamp`), and block number (`Blocknum`).
                    - Parameters (`Params`) can be nested arrays to accommodate functions requiring multiple lists of parameters.
                
                    ### Objective
                    Create {total_tests} new test case objects, each containing more than {total_txs} transactions that might uncover bugs in the contract. 
                    Ensure the transactions use raw values and respect the data types in the function signatures and consider functions modifiers in your transactions.
                    Provide the response as RFC8259 compliant JSON without explanations.
                '''
            }
        ]
        
        return prompt

    def estimate_prompt(self, contact_dir: str, model: str):
        if not os.path.exists(contact_dir):
            raise Exception("not found")
        
        _, contract_abi, _, contract_sol = self._read_contract_files(contact_dir)
        testcase = open('example.json', "r").read()
        
        messages = self._create_prompt(contract_abi, contract_sol, [testcase])
        print (f"Total tokens from prompt: {self._chat_service.count_tokens(messages, model)}")
 
    def count_total_ins(self, contact_dir: str):
        contract_bin_file_name, _, base_contract_name, _ = self._read_contract_files(contact_dir)
        bytecode = open(contract_bin_file_name, "r").read()
        overall_pcs, overall_jumpis = get_pcs_and_jumpis(bytecode)
        print(f"{base_contract_name},{len(overall_pcs)},{len(overall_jumpis)}")
        
    def dump_prompt(self, contact_dir: str, total_tests=10, total_txs=4):
        if not os.path.exists(contact_dir):
            raise Exception("not found")
        
        _, contract_abi, _, contract_sol = self._read_contract_files(contact_dir)
        testcase = open('example.json', "r").read()
                
        messages = self._create_prompt(contract_abi, contract_sol, [testcase], total_tests, total_txs)
        print (self._chat_service.dump_prompt(messages))
        
    def run_llm(self, contact_dir: str, llm: str, model: str, temperature: float, total_tests=10, total_txs=4):
        
        if not os.path.exists(contact_dir):
            raise Exception("not found")
        
        _, contract_abi, base_contract_name, contract_sol  = self._read_contract_files(contact_dir)
        
        testcase = open('example.json', "r").read()        
        messages = self._create_prompt(contract_abi, contract_sol, [testcase], total_tests, total_txs) 
        
        logger.info(f"Requesting test cases for contract {base_contract_name}")
        if llm == "gpt":
            chat_completion = self._chat_service.query_gpt4(messages, model, temperature)
        elif llm == "anyscale": 
            chat_completion = self._chat_service.query_anyscale(messages, model, temperature)
        elif llm == "deepinfra":
            chat_completion = self._chat_service.query_deepinfra(messages, model, temperature)
        elif llm == "ollama":
            chat_completion = self._chat_service.query_ollama(messages, model, temperature)
        elif llm == "fireworks":
            chat_completion = self._chat_service.query_fireworks(messages, model, temperature)
        elif llm == "together":
            chat_completion = self._chat_service.query_together(messages, model, temperature)
        elif llm == "grok":
            chat_completion = self._chat_service.query_grok(messages, model, temperature)
        elif llm == "google":
            chat_completion = self._chat_service.query_google(messages, model, temperature)

        if (chat_completion is not None):
            logger.info(f"New {llm} test case generated!")
            logger.info(f"Is a valid JSON? {is_valid_json(chat_completion)}")
                    
            current_datetime = datetime.now()
            formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")
            
            testcase_file_name = f"{base_contract_name}_{llm}_{model}_{temperature}T_testcase_{formatted_datetime}"
            f = open(os.path.join(contact_dir, testcase_file_name), "w")
            f.write(chat_completion)
            f.close()
            
            prompt_file_name = os.path.join(contact_dir, f"{base_contract_name}_{llm}_{model}_{temperature}T_prompt_{formatted_datetime}")        
            self._chat_service.dump_save_prompt(messages, prompt_file_name)

            logger.info(f"Saving test case {testcase_file_name} and prompt {prompt_file_name}!")
        else: 
            logger.error(f"Error generating seed !")
    
    def convert_to_smartian(self, contract_dir: str, output_dir: str, model="", date= "", with_args=True):
        if not os.path.isdir(contract_dir):
            return
        if (model is None):
            model = ""
        if (output_dir is None):
            output_dir = contract_dir
        if (date is None):
            date = ""
                                    
        _, contract_abi, base_contract_name,_ = self._read_contract_files(contract_dir)
        
        print(f"*{model}*_testcase_{date}*")

        file_list = [file for file in glob.glob(os.path.join(contract_dir, '')+f"*{model}*_testcase_{date}*")]
        if len(file_list) > 0:
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir, ignore_errors=True)
            os.makedirs(output_dir)
            
        file_index = 0
        for file_path in file_list:
            try:
                with open(file_path, 'r') as file:
                    content = file.read()
                    if not is_valid_json(content):
                        content = json_from_text(content)
                        if not is_valid_json(content):
                            raise ValueError("TestCase cant be loaded as JSON")
                    testcases_json = json.loads(content)
                    testcases = TestCase.try_to_adapt_json_testcase(testcases_json)
                    testcase_index = 0
                    for testecase_element in testcases:
                        tc = TestCase(testecase_element)
                        if not tc.is_valid_testcase_struct():
                            raise ValueError("TestCase struct does not respect JSON format")
                        tc_json = tc.process_testcase(contract_abi, with_args)
                        testcase_file_name = f"id-{file_index:05}_{testcase_index:05}"
                        with open(os.path.join(output_dir, testcase_file_name), "w") as f:
                            f.write(json.dumps(tc_json, indent=4))
                        testcase_index += 1
                file_index += 1                        
            except Exception as e:
                logger.error(f"Exeption {e}, file {file_path}")
                continue

    def seed_uniqueness_ratio(self, root_contract_dir: str, model="", date= ""):
        if not os.path.isdir(root_contract_dir):
            return
        total_seeds = 0
        total_duplicate_seeds = 0
        
        for contract_dir in os.listdir(root_contract_dir):            
            full_path = os.path.join(root_contract_dir, contract_dir)
            file_list = [file for file in glob.glob(os.path.join(full_path, '')+f"*{model}*_testcase_{date}*")]

            for file_path in file_list:
                hash_set = set()
                #print(file_path)
                try:
                    with open(file_path, 'r') as file:
                        content = file.read()
                        if not is_valid_json(content):
                            content = json_from_text(content)
                            if not is_valid_json(content):
                                continue
                        testcases_json = json.loads(content)
                        testcases = TestCase.try_to_adapt_json_testcase(testcases_json)
                        for testecase_element in testcases:
                            tc = TestCase(testecase_element)
                            obj_hash = tc.get_testcase_hash(["Blocknum", "Timestamp"])
                            #print(obj_hash)
                            if obj_hash in hash_set:
                                #print(f"Duplicate found")
                                total_duplicate_seeds += 1
                            else:
                                hash_set.add(obj_hash)
                            total_seeds += 1
                except Exception as e:
                    logger.error(f"Exception somewhere {e} {file_path}")
                    continue

        seed_dir = self._extract_deepest_name(root_contract_dir) or root_contract_dir
        temperature = re.search(r'(\d+\.\d+)', seed_dir).group(1)
        print(f"{model},{temperature},{seed_dir},{total_seeds},{total_duplicate_seeds}")
            
    def seed_valid_ratio(self, root_contract_dir: str, model="", date= ""):
        if not os.path.isdir(root_contract_dir):
            return
    
        total_seeds = 0
        total_files_with_invalid_json = 0
        total_files = 0
        total_seeds_with_invalid_struct = 0
        total_args_in_seeds = 0
        total_functions_in_seeds = 0
        total_invalid_function_in_seeds = 0
        total_invalid_args_in_seeds = 0

        for contract_dir in os.listdir(root_contract_dir):
            full_path = os.path.join(root_contract_dir, contract_dir)
                                    
            _, contract_abi, _,_ = self._read_contract_files(full_path)
        
            file_list = [file for file in glob.glob(os.path.join(full_path, '')+f"*{model}*_testcase_{date}*")]
            for file_path in file_list:
                try:
                    with open(file_path, 'r') as file:
                        total_files += 1
                        content = file.read()
                        if not is_valid_json(content):
                            content = json_from_text(content)
                            if not is_valid_json(content):
                                #logger.error(f"Invalid JSON file {file_path}")                            
                                total_files_with_invalid_json += 1
                                continue
                        testcases_json = json.loads(content)
                        testcases = TestCase.try_to_adapt_json_testcase(testcases_json)
                        for testecase_element in testcases:
                            total_seeds += 1                            
                            tc = TestCase(testecase_element)
                            if not tc.is_valid_testcase_struct():
                                total_seeds_with_invalid_struct += 1
                            tc.process_testcase(contract_abi, True)
                            totals = tc.get_validation_totals()
                            total_args_in_seeds += totals[0][0]
                            total_invalid_args_in_seeds += totals[0][1]                            
                            total_functions_in_seeds += totals[1][0]
                            total_invalid_function_in_seeds += totals[1][1]
                except Exception as e:
                    logger.error(f"Exception somewhere {e} {file_path}")
                    continue

        seed_dir = self._extract_deepest_name(root_contract_dir) or root_contract_dir
        temperature = re.search(r'(\d+\.\d+)', seed_dir).group(1)
        print(f"{model},{temperature},{seed_dir},{total_files},{total_files_with_invalid_json},{total_seeds},{total_seeds_with_invalid_struct},{total_args_in_seeds},{total_invalid_args_in_seeds},{total_functions_in_seeds},{total_invalid_function_in_seeds}")
        
    def seed_coverage_ratio(self, root_contract_dir: str, model="", date= ""):
        if not os.path.isdir(root_contract_dir):
            return
    
        total_seeds = 0
        coverage_map = defaultdict(list)
        
        for contract_dir in os.listdir(root_contract_dir):
            full_path = os.path.join(root_contract_dir, contract_dir)
                                    
            contract_bin, contract_abi, _,_ = self._read_contract_files(full_path)
        
            file_list = [file for file in glob.glob(os.path.join(full_path, '')+f"*{model}*_testcase_{date}*")]        

            for file_path in file_list:
                try:
                    with open(file_path, 'r') as file:
                        total_seeds += 1
                        content = file.read()
                        if not is_valid_json(content):
                            content = json_from_text(content)
                            if not is_valid_json(content):
                                continue
                        testcases_json = json.loads(content)
                        testcases = TestCase.try_to_adapt_json_testcase(testcases_json)
                        for testecase_element in testcases:
                            tc = TestCase(testecase_element)                            
                            testdata = json.dumps(tc.process_testcase(contract_abi, True))
                            tmp_test_file = tempfile.NamedTemporaryFile(delete=True, mode='w')
                            tmp_test_file.write(testdata)
                            tmp_test_file.flush()
                            coverage = self.run_smartian(contract_bin, tmp_test_file.name)
                            tmp_test_file.close()      
                            coverage_map[os.path.basename(file_path)].append(coverage.strip())
                except Exception as e:
                    logger.error(f"Exception somewhere {e} {file_path}")
                    continue

        seed_dir = self._extract_deepest_name(root_contract_dir) or root_contract_dir
        temperature = re.search(r'(\d+\.\d+)', seed_dir).group(1)

        for key, values in coverage_map.items():
            for index, value in enumerate(values, start=1):
                contract = key.split("_", 1)[0]
                print(f"{contract},{temperature},{index},{model},{key},{value}")
