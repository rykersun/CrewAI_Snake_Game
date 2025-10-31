import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from crewai.llm import LLM

# --------------------------------------------------
# 1. 載入 .env 檔案中的環境變數
# --------------------------------------------------
load_dotenv()

# 從 .env 讀取 API Keys 和設定
google_api_key = os.getenv("GOOGLE_API_KEY")
serper_api_key = os.getenv("SERPER_API_KEY")
model_name = os.getenv("GEMINI_MODEL_NAME",
                       "gemini-2.5-pro")  # 如果未設定，預設為 1.5 pro

# 檢查必要的 API Keys
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY 環境變數未設定。請檢查您的 .env 檔案。")
if not serper_api_key:
    raise ValueError("SERPER_API_KEY 環境變數未設定。請檢查您的 .env 檔案。")

# --------------------------------------------------
# 2. 設定 LLM (Gemini) 和 Tools (Serper)
# --------------------------------------------------


gemini_llm = LLM(
    model=f"gemini/{model_name}",  # 像這樣 'gemini/gemini-1.5-pro-latest'
    config={
        "api_key": google_api_key
    }
)

# 設定 Serper 搜尋工具
# (這會自動使用 .env 中讀取到的 SERPER_API_KEY)
search_tool = SerperDevTool()

# --------------------------------------------------
# 3. 定義您的 Agents (代理人)
# --------------------------------------------------

# 定義一個市場研究員 (現在具備搜尋能力)
researcher = Agent(
    role='資深市場研究員',
    goal='找出 2025 年最值得關注的 AI 趨勢',
    backstory="""您是一位經驗豐富的市場研究員，
  專門分析新興技術，並能精準預測下一個重大趨勢。
  您會使用您的網路搜尋工具來獲取最新資訊。""",
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm,
    tools=[search_tool]  # <-- 在這裡加入搜尋工具
)

# 定義一個技術作家
writer = Agent(
    role='專業技術內容作家',
    goal='撰寫一篇關於 2025 年 AI 趨勢的引人入勝的部落格文章',
    backstory="""您是一位知名的技術作家，
  擅長將複雜的 AI 概念轉化為易於理解且吸引人的文章。
  您的文章總是能登上技術媒體的頭條。""",
    verbose=True,
    allow_delegation=True,
    llm=gemini_llm
)

# --------------------------------------------------
# 4. 定義您的 Tasks (任務)
# --------------------------------------------------

# 研究任務 (現在會使用搜尋工具)
task_research = Task(
    description="""使用您的搜尋工具，分析當前 AI 領域的發展，
  找出 5 個在 2025 年將會爆發性成長的 AI 趨勢。
  提供每個趨勢的簡要說明及其潛在影響。""",
    expected_output="一份包含 5 個 AI 趨勢及其分析的重點報告。",
    agent=researcher
)

# 寫作任務
task_write = Task(
    description="""使用研究員提供的重點報告，
  撰寫一篇 500 字左右的部落格文章。
  文章風格應具前瞻性、吸引人，並適合大眾閱讀。""",
    expected_output="一篇格式完整、引人入勝的部落格文章。",
    agent=writer
)

# --------------------------------------------------
# 5. 建立並執行 Crew (團隊)
# --------------------------------------------------

my_crew = Crew(
    agents=[researcher, writer],
    tasks=[task_research, task_write],
    process=Process.sequential,
    verbose=True
)

# --------------------------------------------------
# 6. 啟動任務
# --------------------------------------------------

print("==================================================")
print("🚀 啟動 CrewAI 任務 (使用 .env 設定)...")
print(f"使用模型: {model_name}")
print("==================================================")

result = my_crew.kickoff()

print("\n\n==================================================")
print("✅ 任務完成！")
print("==================================================")
print("最終產出結果：\n")
print(result)
