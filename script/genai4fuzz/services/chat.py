import os
import time
import json
import tokencost
import configparser
from loguru import logger
from openai import OpenAI
from datetime import datetime

from genai4fuzz.utils.singleton import SingletonMeta
from genai4fuzz.config import Config

class ChatService(metaclass=SingletonMeta):

    def __init__(self) -> None:
        self._config = Config()
        self._providers = configparser.ConfigParser()
        with open('providers.ini', 'r') as f:
            file_content = f.read()
            file_content_with_section = "[default]\n" + file_content
        self._providers.read_string(file_content_with_section)

    def _query_providers(self, key):
        section = 'default'
        if self._providers.has_option(section, key):
            return self._providers.get(section, key)
        else:
            return None
    
    def count_tokens(self, prompt_msgs: list, model: str):
        final_prompt = '\n'.join([message["content"].strip() for message in prompt_msgs])
        return tokencost.count_string_tokens(final_prompt, model)

    def dump_save_prompt(self, prompt_msgs: list, prompt_filename: str):
        final_prompt = self.dump_prompt(prompt_msgs)
        self.save_to_seeds(prompt_filename, final_prompt)
        
    def dump_prompt(self, prompt_msgs: list):
        return '\n'.join([message["content"] for message in prompt_msgs])

    def save_to_seeds(self, prompt_filename, final_prompt):
        f = open(prompt_filename, "w")
        f.write(final_prompt)
        f.close()

    def query_ollama(self, prompt_msgs: list, model: str, temperature=1) -> str:
        max_tokens = 8192
    
        model_string = self._query_providers(f"ollama.model.{model}")
        if model_string is None:
            logger.error(f"Model {model} not found.")
            exit(0)

        provider_url = self._query_providers(f"ollama.url")
        if provider_url is None:
            logger.error(f"Provider url not found.")
            exit(0)

        logger.info(f"Invoke Ollama with max_tokens={max_tokens} and model {model_string}")
        t_start = time.time()
        client = OpenAI(
            base_url = provider_url,
            api_key = "ollama"
        )
        
        response = client.chat.completions.create(
            messages = prompt_msgs,
            model = model_string,
            max_tokens = max_tokens,
            temperature = temperature)

        g_time = time.time() - t_start
        logger.info(f"Ollama response time: {g_time}")
        
        logger.info(f"Prompt tokens: {response.usage.prompt_tokens}, Completition tokens {response.usage.completion_tokens}")        
        return response.choices[0].message.content

    def query_fireworks(self, prompt_msgs: list, model: str, temperature=1) -> str:
        max_tokens = 8192

        if "FIREWORKS_API_KEY" not in os.environ:
            logger.error("FIREWORKS_API_KEY is not set.")
            exit(0)
    
        model_string = self._query_providers(f"fireworks.model.{model}")
        if model_string is None:
            logger.error(f"Model {model} not found.")
            exit(0)

        provider_url = self._query_providers(f"fireworks.url")
        if provider_url is None:
            logger.error(f"Provider url not found.")
            exit(0)

        logger.info(f"Invoke Fireworks with max_tokens={max_tokens} and model {model_string}")
        t_start = time.time()
        client = OpenAI(
            base_url = provider_url,
            api_key = os.environ["FIREWORKS_API_KEY"]
        )
        
        response = client.chat.completions.create(
            messages = prompt_msgs,
            model = model_string,
            max_tokens = max_tokens,
            temperature = temperature)

        g_time = time.time() - t_start
        logger.info(f"fireworks response time: {g_time}")
        
        logger.info(f"Prompt tokens: {response.usage.prompt_tokens}, Completition tokens {response.usage.completion_tokens}")        
        return response.choices[0].message.content

    def query_together(self, prompt_msgs: list, model: str, temperature=1) -> str:
        max_tokens = 8192

        if "TOGETHER_API_KEY" not in os.environ:
            logger.error("TOGETHER_API_KEY is not set.")
            exit(0)
    
        model_string = self._query_providers(f"together.model.{model}")
        if model_string is None:
            logger.error(f"Model {model} not found.")
            exit(0)

        provider_url = self._query_providers(f"together.url")
        if provider_url is None:
            logger.error(f"Provider url not found.")
            exit(0)

        logger.info(f"Invoke together with max_tokens={max_tokens} and model {model_string}")
        t_start = time.time()
        client = OpenAI(
            base_url = provider_url,
            api_key = os.environ["TOGETHER_API_KEY"]
        )
        
        response = client.chat.completions.create(
            messages = prompt_msgs,
            model = model_string,
            max_tokens = max_tokens,
            temperature = temperature)

        g_time = time.time() - t_start
        logger.info(f"fireworks response time: {g_time}")
        
        logger.info(f"Prompt tokens: {response.usage.prompt_tokens}, Completition tokens {response.usage.completion_tokens}")        
        return response.choices[0].message.content

    def query_deepinfra(self, prompt_msgs: list, model: str, temperature=1) -> str:
        max_tokens = 8192

        if "DEEPINFRA_API_KEY" not in os.environ:
            logger.error("DEEPINFRA_API_KEY is not set.")
            exit(0)
    
        model_string = self._query_providers(f"deepinfra.model.{model}")
        if model_string is None:
            logger.error(f"Model {model} not found.")
            exit(0)

        provider_url = self._query_providers(f"deepinfra.url")
        if provider_url is None:
            logger.error(f"Provider url not found.")
            exit(0)

        logger.info(f"Invoke Deepinfra with max_tokens={max_tokens} and model {model_string}")
        t_start = time.time()
        client = OpenAI(
            base_url=provider_url,
            api_key=os.environ["DEEPINFRA_API_KEY"]
        )
        
        response = client.chat.completions.create(
            messages=prompt_msgs,
            model=model_string,
            #response_format = {"type": "json_object"},
            max_tokens=max_tokens,
            temperature=temperature)

        g_time = time.time() - t_start
        logger.info(f"Deepinfra response time: {g_time}")
        
        logger.info(f"Prompt tokens: {response.usage.prompt_tokens}, Completition tokens {response.usage.completion_tokens}")        
        return response.choices[0].message.content
    
    def query_anyscale(self, prompt_msgs: list, model: str, temperature=1) -> str:
        max_tokens = 8192

        if "ANYSCALE_API_KEY" not in os.environ:
            logger.error("ANYSCALE_API_KEY is not set.")
            exit(0)
    
        model_string = self._query_providers(f"anyscale.model.{model}")
        if model_string is None: 
            logger.error(f"Model {model} not found.")
            exit(0)

        provider_url = self._query_providers(f"anyscale.url")
        if provider_url is None:
            logger.error(f"Provider url not found.")
            exit(0)

        logger.info(f"Invoke Anyscale with max_tokens={max_tokens} and model {model_string}")
        t_start = time.time()
        
        client = OpenAI(
            base_url=provider_url,
            api_key=os.environ["ANYSCALE_API_KEY"]
        )
        
        if model == "Mixtral-8X7B":
            response = client.chat.completions.create(
                messages=prompt_msgs,
                model=model_string,
                response_format = {"type": "json_object"},         
                max_tokens=max_tokens,
                temperature=temperature)
        else:
            response = client.chat.completions.create(
                messages=prompt_msgs,
                model=model_string,
                max_tokens=max_tokens,
                temperature=temperature)
        
        g_time = time.time() - t_start
        logger.info(f"Anyscale response time: {g_time}")
        logger.info(f"Prompt tokens: {response.usage.prompt_tokens}, Completition tokens {response.usage.completion_tokens}")
                
        return response.choices[0].message.content

    def query_gpt4(self, prompt_msgs: list, model: str, temperature=1) -> str:
        max_tokens = 4096

        if "OPENAI_API_KEY" not in os.environ:
            logger.error("OPENAI_API_KEY is not set.")
            exit(0)

        model_string = self._query_providers(f"gpt.model.{model}")
        if model_string is None: 
            logger.error(f"Model {model} not found.")
            exit(0)

        logger.info(f"Invoke GPT {model} with max_tokens={max_tokens}")
        t_start = time.time()

        client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"]
        )

        response = client.chat.completions.create(
            messages=prompt_msgs,
            model=model_string,
            max_tokens=max_tokens,
            temperature=temperature)

        g_time = time.time() - t_start
        logger.info(f"GPT {model} response time: {g_time}")
        logger.info(f"Prompt tokens: {response.usage.prompt_tokens}, Completition tokens {response.usage.completion_tokens}")

        return response.choices[0].message.content