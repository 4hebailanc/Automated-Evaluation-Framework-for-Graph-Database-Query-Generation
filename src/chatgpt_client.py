import requests
# import openai
class ChatGPTClient:
    """
    A client for the OpenAI GPT-3 API that generates text completions based on a given prompt.
    """
    def __init__(self, deployment_name, api_key, api_base, api_version):
        """
        Constructs a new ChatGPTClient instance with the specified API parameters.

        :param deployment_name: The name of the OpenAI deployment to use.
        :param api_key: The API key to use for authentication.
        :param api_base: The base URL of the OpenAI API.
        :param api_version: The version of the OpenAI API to use.
        """
        self.api_url = f"{api_base}/openai/deployments/{deployment_name}/completions?api-version={api_version}"
        # self.api_url = f"{api_base}/openai/deployments?api-version={api_version}"
        self.api_key = api_key
        self.deployment_name = deployment_name
        self.api_version = api_version


    def get_completion(self, prompt, temperature=0, max_tokens=512):
        """
        Generates a text completion based on the given prompt using the OpenAI GPT-3 API.

        :param prompt: The text prompt to use for generating the completion.
        :param temperature: The "creativity" of the completion (higher values lead to more creative but potentially less coherent completions).
        :param max_tokens: The maximum number of tokens (words or symbols) that the completion can be.
        :return: The generated completion text.
        """
        # Construct the JSON payload for the API request
        json_data = {
            'prompt': prompt,
            'temperature': temperature,
            'max_tokens': max_tokens
        }

        messages = [{'role': 'user', 'content': prompt}]
        # print(f"length of prompt is:{int(len(prompt)/4)}")
        # Send the API request
        response = requests.post(self.api_url, json=json_data, headers={'api-key': self.api_key})

        # check the new api for gpt-4
        # response = openai.ChatCompletion.create(engine=self.deployment_name, messages=messages,api_version=self.api_version,)
        # text = response['choices'][0]['message']['content'].replace('\n', '').replace(' .', '.').strip()

                                                # max_tokens=max_tokens,
                                            # temperature=temperature)
        # response = requests.get(self.api_url, json=json_data, headers={'api-key': self.api_key})

        # Parse the response JSON
        try:
            completion = response.json()
            # print(completion['usage'])
            # Check if the content is filtered due to OpenAI's content policies
            if completion['choices'][0]['finish_reason'] == "content_filter":
                print("The generated content is filtered.")
                # Return the generated completion text
            return completion['choices'][0]['text']
        except (KeyError, requests.exceptions.JSONDecodeError):
            print(completion)
            pass