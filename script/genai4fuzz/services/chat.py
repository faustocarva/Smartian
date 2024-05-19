import tiktoken
from loguru import logger
from openai import OpenAI
import os
import time
from datetime import datetime

from genai4fuzz.utils.singleton import SingletonMeta
from genai4fuzz.config import Config

class ChatService(metaclass=SingletonMeta):

    def __init__(self) -> None:
        self._config = Config()

    def _count_tokens(self, model: str, text: list) -> int:
        prompt = '\n'.join([message["content"] for message in text])
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(prompt))

    def _dump_prompt(self, text: list): 
        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"prompt_{formatted_datetime}"
        prompt = '\n'.join([message["content"] for message in text])
        f = open(file_name, "w")
        f.write(prompt)
        f.close()
        
        return
    
    def query_anyscale(self, prompt: str, temperature=0) -> str:
        max_tokens = 4096

        logger.info(f"Invoke Anyscale with max_tokens={max_tokens}")
        t_start = time.time()
        
        client = OpenAI(
            base_url='https://api.endpoints.anyscale.com/v1',
            api_key=os.environ["ANYSCALE_API_KEY"]
        )

        system_message = """
            You are a helpful test case generator assistant with a vast knowledge of Solidity and Ethereum.
            You diligently complete tasks as instructed.
            You only reply with JSON, no other text 
        """

        messages = [
            {"role": "system", "content": system_message},
        ]
        messages += prompt

        response = client.chat.completions.create(
            messages=messages,
            model='meta-llama/Meta-Llama-3-70B-Instruct',
            temperature=temperature)
        
        g_time = time.time() - t_start
        logger.info(f"Anyscale response time: {g_time}")

        self._dump_prompt(messages)
        
        return response.choices[0].message.content

    def query_gpt4(self, prompt: list, temperature=0) -> str:
        max_tokens = 4096

        logger.info(f"Invoke GPT-4 with max_tokens={max_tokens}")
        t_start = time.time()
        
        client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"]
        )

        system_message = """
            You are a helpful test case generator assistant with a vast knowledge of Solidity and Ethereum.
            You diligently complete tasks as instructed.
            You only reply with JSON, no other text 
        """

        messages = [
            {"role": "system", "content": system_message},
        ]
        messages += prompt

        logger.info(f"Total tokens  {self._count_tokens('gpt-4-turbo', messages)}")
        self._dump_prompt(messages)

        response = client.chat.completions.create(
            messages=messages,
            model='gpt-4-turbo',
            temperature=temperature)
        
        g_time = time.time() - t_start
        logger.info(f"GPT-4 response time: {g_time}")

        return response.choices[0].message.content