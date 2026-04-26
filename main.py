from tracemalloc import start

import requests
from datetime import datetime, timedelta
import re
from google import genai
from dotenv import load_dotenv
import os
from datetime import datetime, timezone, timedelta
# 加载配置
load_dotenv()

PROXY = os.getenv("PROXY")
os.environ["HTTP_PROXY"] = PROXY
os.environ["HTTPS_PROXY"] = PROXY
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
AI_MODEL_ID = os.getenv("AI_MODEL_ID")
client = genai.Client(api_key=GEMINI_API_KEY)

GITHUB_PER_PAGE = 15                    # 稍微多抓几个给 AI 挑

# 设置报告展示的周期类型：例如 "周度"、"月度"、"季度" 或 "年度"
REPORT_TYPE = "周度" 

# 设置 GitHub 抓取的精确起止日期 (格式: YYYY-MM-DD)
START_DATE = "2026-04-20"
END_DATE = "2026-04-26"
   

# ==========================================
# 2. 获取 GitHub 数据 (动态时间)
# ==========================================
def get_github_trending(start, end):
    print(f"🔍 正在获取 GitHub 数据区间: {start} 至 {end}...")
    
    url = "https://api.github.com/search/repositories"
    params = {
        "q": f"created:{start}..{end}", 
        "sort": "stars",
        "order": "desc",
        "per_page": GITHUB_PER_PAGE
    }
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"GitHub API 请求失败: {response.status_code}, {response.text}")
        
    data = response.json()
    items = data.get('items', [])
    
    repo_list = []
    for i, repo in enumerate(items):
        full_name = repo.get('full_name') # 获取完整路径用于请求 README
        name = repo.get('name', 'N/A')
        stars = repo.get('stargazers_count', 0)
        language = repo.get('language', '未知')
        desc = repo.get('description', '无描述')
        url = repo.get('html_url', '#')
        created_at_raw = repo.get('created_at')
        if created_at_raw:
            # 1. 把带 Z 的字符串解析为时间对象，并强制指定它是 UTC 时区
            utc_dt = datetime.strptime(created_at_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            
            # 2. 定义北京时间时区 (UTC+8)
            beijing_tz = timezone(timedelta(hours=8))
            
            # 3. 转换到北京时间
            local_dt = utc_dt.astimezone(beijing_tz)
            
            # 4. 格式化为漂亮的字符串，例如 "2023-10-01 20:00:00"
            created_at = local_dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            created_at = '未知'
        
        # --- 新增：抓取 README 详情 ---
        print(f"   📖 正在深度抓取项目详情: {name}...")
        readme_content = get_repo_readme(full_name)
        
        # 将 README 内容整合到发送给 Gemini 的数据中
        repo_info = (
            f"{i+1}. 项目名: {name} | 星标: {stars} | 语言: {language} | 创建时间: {created_at}\n"
            f"   描述: {desc}\n"
            f"   详情(README片段): {readme_content}\n"
            f"   链接: {url}"
        )
        repo_list.append(repo_info)
        
    return "\n\n".join(repo_list)


def get_repo_readme(full_name):
    url = f"https://api.github.com/repos/{full_name}/readme"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            content = response.text
            
            # --- 核心清洗逻辑 ---
            # 1. 去除 HTML 标签 (如 <img...>, <div...>, <a>...)
            clean_text = re.sub(r'<[^>]+>', '', content)
            
            # 2. 去除 Markdown 格式的图片链接 [![]()]
            clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', clean_text)
            
            # 3. 去除多余的空白行和空格
            clean_text = "\n".join([line.strip() for line in clean_text.splitlines() if line.strip()])
            
            # 4. 截取中间部分的干货 (跳过可能存在的剩余链接区)
            # 我们取清洗后内容的前 2000 个字，通常这就包含了项目的真正介绍
            return clean_text[:2000]
            
        return "（无法获取详细内容）"
    except Exception:
        return "（读取出错）"


# ==========================================
# 3. 使用 Gemini 进行总结分析 (动态 Prompt)
# ==========================================
def generate_report_with_gemini(context_data, report_type):
    print("🧠 正在调用 gemini生成报告...")
    
    # 根据天数判断报告类型
    if report_type == "周度":
        # --- 周报模式：深度介绍核心项目 ---
        task_prompt = """
        1. 按照star排序挑选10个项目，对每个项目用一句话极其精简地概括其核心功能，star数。格式：项目名称（star数⭐|语言）：概括。
        2. 挑选出你认为最有价值的 5 个项目，注明项目的发表时间、star数⭐、仓库地址，深度点评，并重点分析它们的【实际应用场景】。
        3. 总结本周的趋势的概要,2-3点。
        4. 标题要具有吸引力，可以包含本周两个热点项目名称。
        """
    elif report_type == "月度":
        # --- 月报模式：广度概括 + 精选点评 ---
        task_prompt = """
        1. 按照star排序挑选10个项目，对每个项目用一句话极其精简地概括其核心功能，star数。格式：项目名称（star数⭐|语言）：概括。
        2. 挑选出你认为最有价值的 5 个项目，注明项目的发表时间、star数⭐、仓库地址，深度点评，并重点分析它们的【实际应用场景】。
        3. 总结本月的趋势的概要。
        4. 标题要具有吸引力，可以包含本月两个热点项目名称。
        """

    full_prompt = f"""
    你是一位资深的开源技术分析师，拥有敏锐的技术洞察力。
    以下是我抓取的 GitHub 最近{report_type}内创建的热门项目列表：
    
    {context_data}
    
    请根据以上数据，生成一份《{report_type}开源热点趋势报告》。
    
    # 任务要求：
    {task_prompt}
    
    # 输出要求：
    - 使用漂亮、专业的 Markdown 排版。
    """
    
    response = client.models.generate_content(
        model=AI_MODEL_ID, 
        contents=full_prompt
    )

    return response.text

# ==========================================
# 4. 主执行流程
# ==========================================
if __name__ == "__main__":
    try:
        # 1. 抓取数据（传入我们设置的天数）
        github_data = get_github_trending(START_DATE, END_DATE)
        
        # 2. 生成报告（传入天数以调整语气）
        final_report = generate_report_with_gemini(github_data, REPORT_TYPE)
        
        print("\n" + "="*50 + " 生成完毕 " + "="*50 + "\n")
        print(final_report)
        
        # 3. 动态命名文件（加上周报或月报的标识）
        report_type = "Weekly" if REPORT_TYPE == "周度" else "Monthly"
        filename = f"output/GitHub_{report_type}_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(final_report)
        print(f"\n✅ 报告已成功保存至本地文件: {filename}")
            
    except Exception as e:
        print(f"❌ 运行过程中发生错误: {e}")