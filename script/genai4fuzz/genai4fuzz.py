from openai import OpenAI

class Genai4fuzz():

    def __init__(self) -> None:
        self._input_service = ""

    def run(self):
        client = OpenAI(
            base_url='http://localhost:8080/v1/',
            # required but ignored
            api_key='ollama',
        )

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    'role': 'user',
                    'content': 'Say this is a test',
                }
            ],
            model='llama3',
        )
        print("Translated text:", chat_completion.choices[0].message)