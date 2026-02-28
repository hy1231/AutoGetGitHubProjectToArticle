import os
from google import genai
from dotenv import load_dotenv

# 加载配置
load_dotenv()

# --- 变量提取 ---
PROXY = os.getenv("PROXY")

os.environ["HTTP_PROXY"] = PROXY
os.environ["HTTPS_PROXY"] = PROXY

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)


model_id = 'gemini-2.5-flash' 

try:
    # 新版 SDK 的调用语法
    response = client.models.generate_content(
        model=model_id,
        contents="hello, who are you?"
    )
    print(response.text)
except Exception as e:
    print(f"调用失败，错误原因: {e}")
