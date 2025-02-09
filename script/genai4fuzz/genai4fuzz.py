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
            
    def _read_contract_files(self, contract_dir):
        if not os.path.isdir(contract_dir):
            raise ValueError(f"Contract directory not found: {contract_dir}")
            
        base_name = os.path.basename(contract_dir.rstrip("/"))
        
        # Build file paths
        abi_file = os.path.join(contract_dir, f"{base_name}.abi")
        bin_file = os.path.join(contract_dir, f"{base_name}.bin") 
        sol_file = os.path.join(contract_dir, f"{base_name}.sol")
        
        # Read ABI file
        with open(abi_file, "r") as f:
            abi_content = f.read()
            
        return bin_file, abi_content, base_name, sol_file      
        
    def _extract_deepest_name(self, path):
        deepest_name = os.path.basename(path)
        if not deepest_name:
            return os.path.basename(os.path.dirname(path))
    
        return deepest_name
        
    def _create_prompt_V2(self, contract_abi: str, contract_sol: str, testcase: list, total_tests=10, total_txs=4) -> list: 
        
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
                'content': """
                    ### Objective:
                    Generate 10 distinct test case objects, designed to uncover potential bugs and vulnerabilities in a Solidity contract. Each test case should adhere to the structure defined below and target common EVM/Solidity vulnerabilities, such as those listed in the SWC Registry and DASP Top 10.                            
                """
            },            
            {
                'role': 'user',
                'content': f'''
                    ### Available Contract Functions:
                    The following Solidity contract functions are available for test case generation:
                    
                    {functions_descs_str}
                '''
            },            
            {
                'role': 'user',
                'content': """
                    ### Test Case Structure

                    Each test case consists of a deployment transaction (`DeployTx`) followed by a sequence of transactions (`Txs`).
                    
                    #### Root
                    - An array of `TestCase` objects.
                    
                    #### DeployTx

                    -   **From**: The deployer's name (e.g., `SmartianAgent1`).
                    -   **Value**: The amount of Ether sent with the deployment transaction (in Wei, use "0" if no Ether is sent).
                    -   **Function**: The constructor function name, which is `constructor`.
                    -   **Params** (optional): The parameters passed to the constructor.
                        -   Parameters can be nested arrays if the function requires it.                    
                    -   **Timestamp**: The timestamp of the deployment transaction (e.g., "10000000").
                    -   **Blocknum**: The block number of the deployment transaction (e.g., "20000000").

                    #### Tx (Transaction)

                    -   **From**: The sender's name (e.g., `SmartianAgent2`).
                    -   **Value**: The amount of Ether sent with the transaction (in Wei, use "0" if no Ether is sent or the function is not payable).
                    -   **Function**: The function name being called.
                    -   **Params** (optional): The parameters passed to the function.
                        -   Use raw values for parameters. For example:
                            -   `address`: Use the full address (e.g., `SmartianAgent1`).
                            -   `uint256`: Use integer literals (e.g., "0", "1", "1000", "115792089237316195423570985008687907853269984665640564039457584007913129639935" (max uint256)).
                        -   Parameters can be nested arrays if the function requires it.
                    -   **Timestamp**: The timestamp of the transaction.
                    -   **Blocknum**: The block number of the transaction.                
                """
            },
            {
                'role': 'user',
                'content': f'''
                    ### Test Case Requirements

                    -   Create {total_tests} test cases.
                    -   Each test case must should contain {total_txs} transactions (`Tx` objects).
                    -   You must respect function parameters and you must not use other function that are not available.
                    -   Vary parameter values across test cases, using boundary values and values that might trigger edge cases.
                    -   Use all four sender contracts (`SmartianAgent1`-`SmartianAgent4`) in diverse roles and combinations.
                    -   Ensure transactions respect function modifiers (e.g., only call `mint` and `unfreeze` from the owner address, send Ether only to the `ico` payable function).
                    -   Generate transactions that might trigger error conditions (e.g., `require` statements, reverts).
                    -   Consider the contract's state and how transactions might change it when designing test cases.
                    -   **The response must be RFC8259 compliant JSON. Do not include any additional text or explanations.**                
                '''
            }
        ]
        
        return prompt
    
    def _create_prompt_V3_fix_funcAsVars_and_removeExample(self, contract_abi: str, contract_sol: str, testcase: list, total_tests=10, total_txs=4) -> list: 
        
        functions_descs = self._sast_service.get_functions_from_ABI_2(contract_abi)

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
            # {
            #     'role': 'user',
            #     'content': '\n### Example \n' + testcase[0]
            # },
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
        
    def _create_prompt_V1_until_10122024(self, contract_abi: str, contract_sol: str, testcase: list, total_tests=10, total_txs=4) -> list: 
        
        #functions_descs = self._sast_service.get_functions_from_ABI_2(contract_abi)
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
        
        messages = self._create_prompt_V1_until_10122024(contract_abi, contract_sol, [testcase])
        print (f"Total tokens from prompt: {self._chat_service.count_tokens(messages, model)}")
  
    def run_smartian(self, program: str, testcase: str):
        fsharp_executable = '../build/Smartian.dll'
        parameters = [f'replay --csvout  -p {program} -i {testcase}']
        cmd = " ".join(['dotnet', fsharp_executable] + parameters)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return result.stdout

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
                
        messages = self._create_prompt_V1_until_10122024(contract_abi, contract_sol, [testcase], total_tests, total_txs)
        print (self._chat_service.dump_prompt(messages))
        
    def run_llm(self, contact_dir: str, llm: str, model: str, temperature: float, total_tests=10, total_txs=4, prompt="V1"):
        
        if not os.path.exists(contact_dir):
            raise Exception("not found")
        
        _, contract_abi, base_contract_name, contract_sol  = self._read_contract_files(contact_dir)
        
        testcase = open('example.json', "r").read()
        if prompt == "V1":
            messages = self._create_prompt_V1_until_10122024(contract_abi, contract_sol, [testcase], total_tests, total_txs) 
        elif prompt == "V2":
            messages = self._create_prompt_V2(contract_abi, contract_sol, [testcase], total_tests, total_txs) 
        
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
        elif llm == "hyperbolic":
            chat_completion = self._chat_service.query_hyperbolic(messages, model, temperature)            

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
    
    def convert_to_smartian(self, contract_dir: str, output_dir: str, model="", date="", with_args=True):
        """
        Convert contract test cases to Smartian format.
        
        Args:
            contract_dir: Directory containing contract files
            output_dir: Output directory for converted files
            model: Model identifier for filtering test cases
            date: Date filter for test cases
            with_args: Whether to include arguments in processing
        """
        # Early returns and default values
        if not os.path.isdir(contract_dir):
            return
        
        output_dir = output_dir or contract_dir
        model = model or ""
        date = date or ""

        # Get contract information
        _, contract_abi, base_contract_name, _ = self._read_contract_files(contract_dir)
        seed_dir = self._extract_deepest_name(contract_dir) or contract_dir

        # Get test files
        file_list = glob.glob(os.path.join(contract_dir, f"*{model}*_testcase_{date}*"))
        if not file_list:
            return

        # Prepare output directory
        os.makedirs(output_dir, exist_ok=True)
        seed_dir_path = os.path.join(output_dir, seed_dir, "seeds")
        if os.path.exists(seed_dir_path):
            shutil.rmtree(seed_dir_path, ignore_errors=True)
        os.makedirs(seed_dir_path)

        # Process each file
        for file_index, file_path in enumerate(file_list):
            try:
                # Read and validate JSON content
                with open(file_path, 'r') as file:
                    content = file.read()
                    if not is_valid_json(content):
                        content = json_from_text(content)
                        if not is_valid_json(content):
                            logger.error(f"Invalid JSON in file {file_path}")
                            continue

                    # Process testcases
                    testcases = TestCase.try_to_adapt_json_testcase(json.loads(content))
                    
                    # Save each testcase
                    for testcase_index, testcase_element in enumerate(testcases):
                        try:
                            tc = TestCase(testcase_element)
                            if not tc.is_valid_testcase_struct():
                                logger.error(f"Invalid testcase structure in {file_path}")
                                continue
                                
                            tc_json = tc.process_testcase(contract_abi, with_args)
                            testcase_file_name = f"id-{file_index:05}_{testcase_index:05}"
                            
                            with open(os.path.join(seed_dir_path, testcase_file_name), "w") as f:
                                json.dump(tc_json, indent=4, fp=f)
                                
                        except Exception as e:
                            logger.error(f"Failed to process testcase {testcase_index} in {file_path}: {str(e)}")
                            continue

            except Exception as e:
                logger.error(f"Failed to process file {file_path}: {str(e)}")
                continue
                
    def seed_metrics(self, root_contract_dir: str, model="", date= "", simple_duplicate = True):
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
        total_duplicate_seeds = 0

        for contract_dir in os.listdir(root_contract_dir):
            full_path = os.path.join(root_contract_dir, contract_dir)

            _, contract_abi, _,_ = self._read_contract_files(full_path)

            file_list = [file for file in glob.glob(os.path.join(full_path, '')+f"*{model}*_testcase_{date}*")]
            for file_path in file_list:
                logger.info(f"Processing file {file_path}")
                uniqueseeds_set = set()
                try:
                    with open(file_path, 'r') as file:
                        total_files += 1
                        content = file.read()
                        if not is_valid_json(content):
                            content = json_from_text(content)
                            if not is_valid_json(content):
                                logger.error(f"Invalid JSON file {file_path}")
                                total_files_with_invalid_json += 1
                                continue
                        testcases_json = json.loads(content)
                        testcases = TestCase.try_to_adapt_json_testcase(testcases_json)
                        for testcase_element in testcases:
                            total_seeds += 1
                            tc = TestCase(testcase_element)
                            
                            if not tc.is_valid_testcase_struct():
                                total_seeds_with_invalid_struct += 1
                                continue
                             
                            if simple_duplicate: 
                                obj_hash = tc.get_testcase_hash(["Blocknum", "Timestamp"])
                            else:
                                obj_hash = tc.get_testcase_hash()
                                
                            if obj_hash in uniqueseeds_set:
                                total_duplicate_seeds += 1
                            else:
                                uniqueseeds_set.add(obj_hash)
                                
                            tc.process_testcase(contract_abi, True)
                            totals = tc.get_validation_totals()
                            total_args_in_seeds += totals[0][0]
                            total_invalid_args_in_seeds += totals[0][1]
                            total_functions_in_seeds += totals[1][0]
                            total_invalid_function_in_seeds += totals[1][1]
                except Exception as e:
                    logger.error(f"Exception {e} {file_path}")
                    continue

        seed_dir = self._extract_deepest_name(root_contract_dir) or root_contract_dir
        temperature = re.search(r'_([^_]*\d+\.\d+)_', seed_dir).group(1)
        print(f"{model},{temperature},{seed_dir},{total_files},{total_files_with_invalid_json},{total_seeds},{total_duplicate_seeds},{total_seeds_with_invalid_struct},{total_args_in_seeds},{total_invalid_args_in_seeds},{total_functions_in_seeds},{total_invalid_function_in_seeds}")
        
    def seed_coverage_ratio(self, root_contract_dir: str, model="", date= "", remove_simple_duplicates=False, remove_full_duplicates=False):
        if not os.path.isdir(root_contract_dir):
            return
    
        total_seeds = 0
        coverage_map = defaultdict(list)
        
        for contract_dir in os.listdir(root_contract_dir):
            full_path = os.path.join(root_contract_dir, contract_dir)
                                    
            contract_bin, contract_abi, _,_ = self._read_contract_files(full_path)
        
            file_list = [file for file in glob.glob(os.path.join(full_path, '')+f"*{model}*_testcase_{date}*")]

            for file_path in file_list:
                logger.info(f"Processing file {file_path}")
                uniqueseeds_set = set()
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
                            if not tc.is_valid_testcase_struct():
                                logger.info(f"Ivalide struct  {file_path}")
                                continue
                            
                            if remove_simple_duplicates or remove_full_duplicates:
                                if remove_simple_duplicates: 
                                    obj_hash = tc.get_testcase_hash(["Blocknum", "Timestamp"])
                                elif remove_full_duplicates:
                                    obj_hash = tc.get_testcase_hash()

                                if obj_hash in uniqueseeds_set:
                                    logger.info(f"Duplicate seed {file_path}")
                                    continue
                                else:
                                    uniqueseeds_set.add(obj_hash)
                                                                
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
        temperature = re.search(r'_([^_]*\d+\.\d+)_', seed_dir).group(1)

        for key, values in coverage_map.items():
            for index, value in enumerate(values, start=1):
                contract = key.split("_", 1)[0]
                print(f"{contract},{temperature},{index},{model},{key},{value}")
