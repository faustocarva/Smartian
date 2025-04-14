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
import genai4fuzz.utils.datafile as datafile

class ChatService(metaclass=SingletonMeta):

    def __init__(self) -> None:
        self._config = Config()
        self._providers = configparser.ConfigParser()

        config_path = datafile.load_data_file("providers.ini")
        
        if not os.path.isfile(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, 'r') as f:
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
        return int(tokencost.count_string_tokens(final_prompt, model))

    def count_message_tokens(self, prompt_msgs: list, model: str):
        final_prompt = '\n'.join([message["content"].strip() for message in prompt_msgs])
        return int(tokencost.count_message_tokens(final_prompt, model))


    def dump_save_prompt(self, prompt_msgs: list, prompt_filename: str):
        final_prompt = self.dump_prompt(prompt_msgs)
        self.save_to_seeds(prompt_filename, final_prompt)
        
    def dump_prompt(self, prompt_msgs: list):
        return '\n'.join([message["content"] for message in prompt_msgs])

    def save_to_seeds(self, prompt_filename, final_prompt):
        f = open(prompt_filename, "w")
        f.write(final_prompt)
        f.close()

    def fetch_chat_completion(self, client, prompt_msgs, model_string, max_tokens, temperature, max_retries=5, backoff_factor=2):
        retries = 0
        
        while retries < max_retries:
            try:
                response = client.chat.completions.create(
                    messages=prompt_msgs,
                    model=model_string,
                    #response_format = {"type": "json_object"},
                    max_tokens=max_tokens,
                    temperature=temperature)
                return response
            
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
            
            retries += 1
            wait_time = backoff_factor ** retries
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        
        return None

    def fetch_chat_completion_anthropic(self, client, prompt_msgs, system, model_string, max_tokens, temperature, max_retries=5, backoff_factor=2):
        retries = 0
        
        while retries < max_retries:
            try:
                response = client.chat.completions.create(
                    messages=prompt_msgs,
                    model=model_string,
                    #system=system,
                    max_tokens=max_tokens,
                    temperature=temperature)
                return response
            
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
            
            retries += 1
            wait_time = backoff_factor ** retries
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        
        return None


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

        limit = self._query_providers(f"fireworks.model.{model}.limit")
        if limit is None:
            limit = 8192
            logger.info(f"Model limit  not found.")

        max_tokens = int(int(limit) - int(self.count_tokens(prompt_msgs, model))*1.3)
        logger.info(f"Invoke fireworks with max_tokens={max_tokens} and model {model_string}")

        client = OpenAI(
            base_url = provider_url,
            api_key = os.environ["FIREWORKS_API_KEY"]
        )
        
        t_start = time.time()
        response = self.fetch_chat_completion(client, prompt_msgs, model_string, max_tokens, temperature)
        g_time = time.time() - t_start
        logger.info(f"fireworks response time: {g_time}")
        if (response is not None):
            logger.info(f"Prompt tokens: {response.usage.prompt_tokens}, Completition tokens {response.usage.completion_tokens}")
            return response.choices[0].message.content
        return None

    def query_together(self, prompt_msgs: list, model: str, temperature=1) -> str:

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

        limit = self._query_providers(f"together.model.{model}.limit")
        if limit is None:
            limit = 8192
            logger.info(f"Model limit  not found.")

        max_tokens = int(int(limit) - (self.count_tokens(prompt_msgs, model)*1.5))
        #max_tokens = limit
        logger.info(f"Invoke together with max_tokens={max_tokens} and model {model_string}")

        client = OpenAI(
            base_url = provider_url,
            api_key = os.environ["TOGETHER_API_KEY"]
        )
        
        t_start = time.time()
        response = self.fetch_chat_completion(client, prompt_msgs, model_string, max_tokens, temperature)
        g_time = time.time() - t_start
        logger.info(f"together response time: {g_time}")
        if (response is not None):
            logger.info(f"Prompt tokens: {response.usage.prompt_tokens}, Completition tokens {response.usage.completion_tokens}")        
            return response.choices[0].message.content
        return None

    def query_deepinfra(self, prompt_msgs: list, model: str, temperature=1) -> str:
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

        limit = self._query_providers(f"deepinfra.model.{model}.limit")
        if limit is None:
            limit = 8192
            logger.info(f"Model limit  not found.")

        max_tokens = int(int(limit) - int(self.count_tokens(prompt_msgs, model))*1.3)
        logger.info(f"Invoke Deepinfra with max_tokens={max_tokens} and model {model_string}")

        client = OpenAI(
            base_url = provider_url,
            api_key = os.environ["DEEPINFRA_API_KEY"]            
        )
        
        t_start = time.time()
        response = self.fetch_chat_completion(client, prompt_msgs, model_string, max_tokens, temperature)
        g_time = time.time() - t_start
        logger.info(f"Deepinfra response time: {g_time}")
        if (response is not None):
            logger.info(f"Prompt tokens: {response.usage.prompt_tokens}, Completition tokens {response.usage.completion_tokens}")
            return response.choices[0].message.content
        return None

    def query_grok(self, prompt_msgs: list, model: str, temperature=1) -> str:
        if "GROK_API_KEY" not in os.environ:
            logger.error("GROK_API_KEY is not set.")
            exit(0)
    
        model_string = self._query_providers(f"grok.model.{model}")
        if model_string is None:
            logger.error(f"Model {model} not found.")
            exit(0)

        provider_url = self._query_providers(f"grok.url")
        if provider_url is None:
            logger.error(f"Provider url not found.")
            exit(0)

        limit = self._query_providers(f"grok.model.{model}.limit")
        if limit is None:
            limit = 8192
            logger.info(f"Model limit  not found.")

        #max_tokens = int(int(limit) - int(self.count_tokens(prompt_msgs, model))*1.3)
        max_tokens = int(limit)
        logger.info(f"Invoke grok with max_tokens={max_tokens} and model {model_string}")

        client = OpenAI(
            base_url = provider_url,
            api_key = os.environ["GROK_API_KEY"]            
        )
        
        t_start = time.time()
        response = self.fetch_chat_completion(client, prompt_msgs, model_string, max_tokens, temperature)
        g_time = time.time() - t_start
        logger.info(f"Grok response time: {g_time}")
        if (response is not None):
            logger.info(f"Prompt tokens: {response.usage.prompt_tokens}, Completition tokens {response.usage.completion_tokens}")
            return response.choices[0].message.content
        return None

    def query_anyscale(self, prompt_msgs: list, model: str, temperature=1) -> str:
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

        limit = self._query_providers(f"anyscale.model.{model}.limit")
        if limit is None:
            limit = 8192
            logger.info(f"Model limit  not found.")

        max_tokens = int(int(limit) - int(self.count_tokens(prompt_msgs, model))*1.3)
        logger.info(f"Invoke grok with max_tokens={max_tokens} and model {model_string}")

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
        max_tokens = 8192

        if "OPENAI_API_KEY" not in os.environ:
            logger.error("OPENAI_API_KEY is not set.")
            exit(0)

        model_string = self._query_providers(f"gpt.model.{model}")
        if model_string is None: 
            logger.error(f"Model {model} not found.")
            exit(0)

        limit = self._query_providers(f"gpt.model.{model}.limit")
        if limit is None:
            limit = 8192
            logger.info(f"Model limit  not found.")
        
        
        max_tokens = int(int(limit) - int(self.count_tokens(prompt_msgs, model))*1.3)
        logger.info(f"Invoke GPT {model} with max_tokens={max_tokens}")
        t_start = time.time()

        client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"]
        )

        t_start = time.time()
        response = self.fetch_chat_completion(client, prompt_msgs, model_string, max_tokens, temperature)
        g_time = time.time() - t_start
        logger.info(f"GPT {model} response time: {g_time}")        
        if (response is not None):
            logger.info(f"Prompt tokens: {response.usage.prompt_tokens}, Completition tokens {response.usage.completion_tokens}")        
            return response.choices[0].message.content
        return None
    
    def query_google(self, prompt_msgs: list, model: str, temperature=1) -> str:
        if "GOOGLE_API_KEY" not in os.environ:
            logger.error("GOOGLE_API_KEY is not set.")
            exit(0)
    
        model_string = self._query_providers(f"gemini.model.{model}")
        if model_string is None:
            logger.error(f"Model {model} not found.")
            exit(0)

        provider_url = self._query_providers(f"gemini.url")
        if provider_url is None:
            logger.error(f"Provider url not found.")
            exit(0)

        limit = self._query_providers(f"gemini.model.{model}.limit")
        if limit is None:
            limit = 8192
            logger.info(f"Model limit  not found.")

        #max_tokens = int(int(limit) - int(self.count_tokens(prompt_msgs, model))*1.3)
        max_tokens = int(limit)
        logger.info(f"Invoke gemini with max_tokens={max_tokens} and model {model_string}")

        client = OpenAI(
            base_url = provider_url,
            api_key = os.environ["GOOGLE_API_KEY"]            
        )
        
        t_start = time.time()
        response = self.fetch_chat_completion(client, prompt_msgs, model_string, max_tokens, temperature)
        g_time = time.time() - t_start
        logger.info(f"gemini response time: {g_time}")
        if (response is not None):
            logger.info(f"Prompt tokens: {response.usage}")        
            return response.choices[0].message.content
        return None
    
    
    def query_hyperbolic(self, prompt_msgs: list, model: str, temperature=1) -> str:

        if "HYPERBOLIC_API_KEY" not in os.environ:
            logger.error("HYPERBOLIC_API_KEY is not set.")
            exit(0)
    
        model_string = self._query_providers(f"hyperbolic.model.{model}")
        if model_string is None:
            logger.error(f"Model {model} not found.")
            exit(0)

        provider_url = self._query_providers(f"hyperbolic.url")
        if provider_url is None:
            logger.error(f"Provider url not found.")
            exit(0)

        limit = self._query_providers(f"hyperbolic.model.{model}.limit")
        if limit is None:
            limit = 8192
            logger.info(f"Model limit  not found.")

        max_tokens = int(int(limit) - (self.count_tokens(prompt_msgs, model)*1.5))
        logger.info(f"Invoke hyperbolic with max_tokens={max_tokens} and model {model_string}")

        client = OpenAI(
            base_url = provider_url,
            api_key = os.environ["HYPERBOLIC_API_KEY"]
        )
        
        t_start = time.time()
        response = self.fetch_chat_completion(client, prompt_msgs, model_string, max_tokens, temperature)
        g_time = time.time() - t_start
        logger.info(f"hyperbolic response time: {g_time}")
        if (response is not None):
            logger.info(f"Prompt tokens: {response.usage.prompt_tokens}, Completition tokens {response.usage.completion_tokens}")
            return response.choices[0].message.content
        return None

    
    def query_sambanova(self, prompt_msgs: list, model: str, temperature=1) -> str:

        if "SAMBANOVA_API_KEY" not in os.environ:
            logger.error("SAMBANOVA_API_KEY is not set.")
            exit(0)
    
        model_string = self._query_providers(f"sambanova.model.{model}")
        if model_string is None:
            logger.error(f"Model {model} not found.")
            exit(0)

        provider_url = self._query_providers(f"sambanova.url")
        if provider_url is None:
            logger.error(f"Provider url not found.")
            exit(0)

        limit = self._query_providers(f"sambanova.model.{model}.limit")
        if limit is None:
            limit = 8192
            logger.info(f"Model limit  not found.")

        max_tokens = int(int(limit) - (self.count_tokens(prompt_msgs, model)*1.5))
        logger.info(f"Invoke sambanova with max_tokens={max_tokens} and model {model_string}")

        client = OpenAI(
            base_url = provider_url,
            api_key = os.environ["SAMBANOVA_API_KEY"]
        )
        
        t_start = time.time()
        response = self.fetch_chat_completion(client, prompt_msgs, model_string, max_tokens, temperature)
        g_time = time.time() - t_start
        logger.info(f"sambanova response time: {g_time}")
        if (response is not None):
            logger.info(f"Prompt tokens: {response.usage.prompt_tokens}, Completition tokens {response.usage.completion_tokens}")
            return response.choices[0].message.content
        return None
    
    
    def query_anthropic(self, prompt_msgs: list, model: str, temperature=1) -> str:
        max_tokens = 8192

        if "ANTHROPIC_API_KEY" not in os.environ:
            logger.error("ANTHROPIC_API_KEY is not set.")
            exit(0)

        provider_url = self._query_providers(f"anthropic.url")
        if provider_url is None:
            logger.error(f"Provider url not found.")
            exit(0)

        model_string = self._query_providers(f"anthropic.model.{model}")
        if model_string is None: 
            logger.error(f"Model {model} not found.")
            exit(0)

        limit = self._query_providers(f"anthropic.model.{model}.limit")
        if limit is None:
            logger.info(f"Model limit  not found.")
                        
        if prompt_msgs and prompt_msgs[0]["role"] == "system":
            system = prompt_msgs.pop(0)["content"]
        else:
            system = ""                
        
        max_tokens = 16384
        logger.info(f"Invoke anthropic {model} with max_tokens={max_tokens}")
        t_start = time.time()

        client = OpenAI(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            base_url=provider_url
        )

        t_start = time.time()
        response = self.fetch_chat_completion_anthropic(client, prompt_msgs, system, model_string, max_tokens, temperature)
        g_time = time.time() - t_start
        logger.info(f"anthropic {model} response time: {g_time}")        
        if (response is not None):
            logger.info(f"Prompt tokens: {response.usage.prompt_tokens}, Completition tokens {response.usage.completion_tokens}")        
            return response.choices[0].message.content
        return None
    