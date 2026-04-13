from google import genai  # 你现在的导入方式
from dotenv import load_dotenv
import os

# 加载配置
load_dotenv()
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- 关键改动：创建 Client 对象 ---
client = genai.Client(api_key=GEMINI_API_KEY)

print("--- 当前可用的模型列表 ---")

# --- 关键改动：使用 client.models.list() ---
for m in client.models.list():
    # 新版 SDK 的模型对象属性与旧版略有不同
    # 我们可以直接打印名称来看看
    print(f"可用模型 ID: {m.name}")