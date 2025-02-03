import json
import re
from eth_utils import function_signature_to_4byte_selector
from loguru import logger
from slither.slither import Slither


from genai4fuzz.utils.singleton import SingletonMeta
from genai4fuzz.config import Config

class SastService(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._config = Config()
        
        
    def get_function_signatures_mod(self, contract_file, target_functions):
        try:
            slither = Slither(contract_file)
            sigs = {}
            
            for contract in slither.contracts_derived:
                for function in contract.functions:
                    param_types = [param.type.__str__() for param in function.parameters]
                    returns = [ret.type.__str__() for ret in function.return_values]
                    signature = f"{function.name}({','.join(param_types)})"
                    
                    if function.visibility == 'public' and signature in target_functions:
                        sigs[signature] = {
                            'modifiers': [m.name for m in function.modifiers],
                            'returns': returns
                        }
                        
            result = []
            for func in target_functions:
                if func in sigs:
                    mods = ' '.join(sigs[func]['modifiers'])
                    returns_str = f" returns ({','.join(sigs[func]['returns'])})" if sigs[func]['returns'] else ""
                    result.append(f"{func}{' ' + mods if mods else ''}{returns_str}")
                else:
                    result.append(func)
            
            return result
        except Exception as e:
            logger.error(f"Slither Exception in file {contract_file}")
            return None
    
    def get_function_modifiers(self, contract_file, target_functions):
        try:
            slither = Slither(contract_file)
            modifiers = {}
            
            for contract in slither.contracts_derived:
                for function in contract.functions:
                    param_types = [param.type.__str__() for param in function.parameters]
                    signature = f"{function.name}({','.join(param_types)})"
                    if function.visibility == 'public' and signature in target_functions:
                        for modifier in function.modifiers:
                            modifiers[signature] = [modifier.name] + modifiers.get(signature, [])
                                            
            for key in modifiers.keys():
                i = target_functions.index(key)
                modifiers_str = ' '.join([modifier_str for modifier_str in modifiers[key]])
                target_functions[i] = f"{target_functions[i]} {modifiers_str}"
            
            return target_functions
        except Exception as e:
            logger.error(f"Slither Exeption in file {contract_file}")
            return None

    def get_interface_from_abi(self, abi):
        abi = json.loads(abi)        
        interface = {}
        for field in abi:
            if field['type'] == 'function':
                function_name = field['name']
                function_inputs = []
                signature = function_name + '('
                for i in range(len(field['inputs'])):
                    input_type = field['inputs'][i]['type']
                    function_inputs.append(input_type)
                    signature += input_type
                    if i < len(field['inputs']) - 1:
                        signature += ','
                signature += ')'
                hash = function_signature_to_4byte_selector(signature).hex()
                interface[hash] = function_name, function_inputs
            elif field['type'] == 'constructor':
                function_inputs = []
                for i in range(len(field['inputs'])):
                    input_type = field['inputs'][i]['type']
                    function_inputs.append(input_type)
                interface['constructor'] = 'constructor', function_inputs, 
            elif field['type'] == 'fallback':
                func_signature = 'fallback()'
                hash = function_signature_to_4byte_selector(func_signature).hex()
                interface[hash] = "fallback",[]

        return interface

    def get_functions_from_ABI(self, abi: str):
        abi = json.loads(abi)
        functions = []
        for item in abi:
            if item.get('type') == 'function':
                payable = " payable " if item.get('payable', False) or item.get('stateMutability') == 'payable' else ""
                func_signature = item['name'] + '(' + ','.join([input['type'] for input in item['inputs']]) + ')' + payable
            elif item.get('type') == 'constructor':
                func_signature = 'constructor' + '(' + ','.join([input['type'] for input in item['inputs']]) + ')'
            elif item.get('type') == 'fallback':
                func_signature = 'fallback()'
            else:
                continue
            
            functions.append(f'{func_signature}')

        return functions
    
    def get_function_selector(self, abi: str, function: str):
        abi = json.loads(abi)
        selector = None
        for item in abi:
            #Smartian has a bug with functions with same name and different args, loop til the end, as smartian to make same selector
            if item.get('name') == function:
                func_signature = item['name'] + '(' + ','.join([input['type'] for input in item['inputs']]) + ')'
                selector = function_signature_to_4byte_selector(func_signature).hex()
            elif item.get('type') == 'fallback' and (function == "fallback" or function == "fallback()"):
                func_signature = 'fallback()'
                selector = function_signature_to_4byte_selector(func_signature).hex()
            elif item.get('type') == 'constructor' and item.get('name') == function:
                func_signature = "constructor" + '(' + ','.join([input['type'] for input in item['inputs']]) + ')'
                selector = function_signature_to_4byte_selector(func_signature).hex()
                
        return selector
    
    def remove_comments_from_contract(self, contract):
        # Remove single-line comments
        no_single_line_comments = re.sub(r'//.*$', '', contract, flags=re.MULTILINE)
        
        # Remove multi-line comments
        no_multi_line_comments = re.sub(r'/\*[\s\S]*?\*/', '', no_single_line_comments, flags=re.DOTALL)
        
        return no_multi_line_comments