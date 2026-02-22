import requests
from datetime import datetime, timedelta
import google.generativeai as genai

# ==========================================
# 1. 配置参数 (核心控制区)
# ==========================================
GEMINI_API_KEY = "AIzaSyDblVam4AhxVQ5l5ezISYqSMZbYwj33CSA"  # 替换为你的 Gemini API Key
GITHUB_PER_PAGE = 15                    # 稍微多抓几个给 AI 挑

# 👇 这里是关键！你可以随便改成 7 (周报) 或者 30 (月报)
REPORT_DAYS = 7                         

# ==========================================
# 2. 获取 GitHub 数据 (动态时间)
# ==========================================
def get_github_trending(days):
    print(f"🔍 正在获取 GitHub 最近 {days} 天的热门项目...")
    
    # 动态计算 N 天前的日期
    target_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    url = "https://api.github.com/search/repositories"
    params = {
        "q": f"created:>={target_date}",
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
        name = repo.get('name', 'N/A')
        stars = repo.get('stargazers_count', 0)
        language = repo.get('language', '未知')
        desc = repo.get('description', '无描述')
        url = repo.get('html_url', '#')
        
        repo_info = f"{i+1}. 项目名: {name} | 星标: {stars} | 语言: {language}\n   描述: {desc}\n   链接: {url}"
        repo_list.append(repo_info)
        
    return "\n\n".join(repo_list)

# ==========================================
# 3. 使用 Gemini 进行总结分析 (动态 Prompt)
# ==========================================
def generate_report_with_gemini(context_data, days):
    print("🧠 正在根据报告周期切换 AI 分析模式...")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash') # 建议使用最新模型
    
    today = datetime.now().strftime('%Y年%m月%d日')
    
    # 根据天数判断报告类型
    if days <= 7:
        # --- 周报模式：深度介绍核心项目 ---
        period_name = "一周"
        task_prompt = """
        1. 【核心精选】：从列表中挑选出 5 个最具有潜力和技术价值的项目。
        2. 【深度点评】：对每个项目进行详细介绍，包括：它解决了什么技术痛点、其核心亮点是什么、以及它为什么能在这个月获得高星标。
        """
    else:
        # --- 月报模式：广度概括 + 精选点评 ---
        period_name = "一月"
        task_prompt = """
        1. 【全景回顾】：对列表中的每个项目，用**一句话**极其精简地概括其核心功能。
        2. 【TOP 3 价值榜】：从中挑选出你认为本月**最有价值的 3 个项目**，进行深度点评，并重点分析它们的【实际应用场景】（例如：适合个人开发者提效、或是适合企业级大规模部署）。
        """

    prompt = f"""
    你是一位资深的开源技术分析师，拥有敏锐的技术洞察力。今天是 {today}。
    以下是我抓取的 GitHub 最近 {days} 天内创建的热门项目列表：
    
    {context_data}
    
    请根据以上数据，生成一份《{period_name}开源热点趋势报告》。
    
    # 任务要求：
    {task_prompt}
    
    3. 【技术趋势观察】：根据本报告期内所有项目的分布，总结一段技术趋势观察（例如：某种新架构的流行、AI 赛道的细分化等）。
    
    # 输出要求：
    - 使用专业的 Markdown 排版。
    - 标题要具有吸引力，能够体现出本周/本月的技术风向。
    """
    
    response = model.generate_content(prompt)
    return response.text

# ==========================================
# 4. 主执行流程
# ==========================================
if __name__ == "__main__":
    try:
        # 1. 抓取数据（传入我们设置的天数）
        github_data = get_github_trending(REPORT_DAYS)
        
        # 2. 生成报告（传入天数以调整语气）
        final_report = generate_report_with_gemini(github_data, REPORT_DAYS)
        
        print("\n" + "="*50 + " 生成完毕 " + "="*50 + "\n")
        print(final_report)
        
        # 3. 动态命名文件（加上周报或月报的标识）
        report_type = "Weekly" if REPORT_DAYS <= 7 else "Monthly"
        filename = f"GitHub_{report_type}_Report_{datetime.now().strftime('%Y%m%d')}.md"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(final_report)
        print(f"\n✅ 报告已成功保存至本地文件: {filename}")
            
    except Exception as e:
        print(f"❌ 运行过程中发生错误: {e}")