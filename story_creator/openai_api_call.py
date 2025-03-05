import openai
import time

openai_client = openai.OpenAI()


'''
# Ensure the OpenAI API key is set in your environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
openai.api_key = openai_api_key
'''

def call_openai(messages, model="gpt-4o-mini"):
    t = time.time()
    response = openai_client.chat.completions.create(
        model=model,
        messages=messages
    )
    print(f'API request took {time.time() - t}')

    # Parse the assistant's reply
    assistant_reply = response.choices[0].message.content
    if assistant_reply.startswith('```json') and assistant_reply.endswith('```'):
        assistant_reply = assistant_reply[8:-4]

    return assistant_reply
