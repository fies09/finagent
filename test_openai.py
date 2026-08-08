import os
import openai
from dotenv import load_dotenv

load_dotenv()

client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://cloud.yiyongai.cn/v1"
)

def test_chat(model_name):
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "说明一下什么是 moe模型 ？"}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"ERROR: {e}"

if __name__ == "__main__":
    models = ["claude-sonnet-4-6", "claude-opus-4-6", "claude-opus-4-7", "claude-opus-4-8", "gpt-5.5"]
    for m in models:
        print(f"[{m}] {test_chat(m)}")
