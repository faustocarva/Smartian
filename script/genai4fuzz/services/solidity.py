from loguru import logger
from openai import OpenAI
import os
import time

from genai4fuzz.utils.singleton import SingletonMeta
from genai4fuzz.config import Config

class Solidity(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._config = Config()
