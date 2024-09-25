import os
import time
import re
from loguru import logger
from slither.slither import Slither


from genai4fuzz.utils.singleton import SingletonMeta
from genai4fuzz.config import Config

class SastService(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._config = Config()
    
    def remove_comments_from_contract(self, contract):
        # Remove single-line comments
        no_single_line_comments = re.sub(r'//.*$', '', contract, flags=re.MULTILINE)
        
        # Remove multi-line comments
        no_multi_line_comments = re.sub(r'/\*[\s\S]*?\*/', '', no_single_line_comments, flags=re.DOTALL)
        
        return no_multi_line_comments