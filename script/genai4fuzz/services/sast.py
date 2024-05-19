from loguru import logger
import os
import time
from slither.slither import Slither

from genai4fuzz.utils.singleton import SingletonMeta
from genai4fuzz.config import Config

class SastService(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._config = Config()
    
