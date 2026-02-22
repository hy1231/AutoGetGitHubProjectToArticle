import os
import google.generativeai as genai

os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10809"

# 显式指定 API 路径和模型
genai.configure(api_key="AIzaSyDblVam4AhxVQ5l5ezISYqSMZbYwj33CSA")

def test_ai():
    # 尝试列出你账户下所有可用的模型名称
    print("🔍 正在拉取可用模型列表...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"可用模型: {m.name}")
        
        # 使用列出来的完整名称，例如 'models/gemini-1.5-flash'
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Ping")
        print(f"✅ AI 回复: {response.text}")
    except Exception as e:
        print(f"❌ 依旧失败: {e}")

test_ai()