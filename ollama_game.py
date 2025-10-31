import os
import subprocess
import sys
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# ----------------------------
# 1. 設定你的 LLM
# ----------------------------
ollama_llm = LLM(
    model="ollama/openhermes:latest",
    base_url="http://192.168.68.107:11434",
    temperature=0.1
)

# ----------------------------
# 2. 建立自訂工具 (Custom Tool)
# ----------------------------


class CodeExecutionTool(BaseTool):
    name: str = "code_execution_tool"
    description: str = "接收一段 Python 程式碼字串,將其儲存為 'generated_snake_game.py' 檔案,然後執行它。它會回報執行是否成功,或者捕捉並回報錯誤訊息。"

    last_tested_code: str = ""  # 儲存最後測試的程式碼

    def _run(self, code: str) -> str:
        """
        執行傳入的 Python 程式碼字串。
        """
        # 儲存這次測試的程式碼
        self.last_tested_code = code

        # 1. 確保 pygame 已經安裝
        try:
            import pygame
        except ImportError:
            print("Pygame not found, attempting to install...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install",
                               "pygame"], check=True, capture_output=True, text=True)
                print("Pygame installed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install pygame: {e.stderr}")
                return f"工具錯誤: 無法安裝 pygame。錯誤訊息: {e.stderr}"

        # 2. 將程式碼寫入檔案
        filepath = "generated_snake_game.py"
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
            print(f"Code successfully written to {filepath}")
        except Exception as e:
            return f"工具錯誤: 無法寫入檔案。錯誤訊息: {str(e)}"

        # 3. 執行程式碼
        try:
            print(
                f"Attempting to execute '{sys.executable} {filepath}' with a 10-second timeout...")
            process = subprocess.run(
                [sys.executable, filepath],
                capture_output=True,
                text=True,
                timeout=10
            )

            if process.returncode != 0:
                print(f"Execution failed. Error: {process.stderr}")
                return f"執行失敗: 程式碼有錯誤。\n錯誤訊息:\n{process.stderr}"
            else:
                print("Execution finished gracefully (unexpected for a game loop).")
                return f"執行成功 (程式正常結束)。\n輸出:\n{process.stdout}"

        except subprocess.TimeoutExpired:
            print("Execution timeout occurred (This is EXPECTED for a game loop).")
            return "執行成功: 程式碼成功運行 10 秒而沒有崩潰 (遊戲迴圈已啟動)。"

        except Exception as e:
            return f"執行時發生未預期的錯誤: {str(e)}"

        finally:
            # 4. 清理檔案
            if os.path.exists(filepath):
                os.remove(filepath)
            print(f"Cleaned up {filepath}")


# ----------------------------
# 3. 實例化你的工具
# ----------------------------
code_executor = CodeExecutionTool()

# ----------------------------
# 4. 定義你的 Agents
# ----------------------------

# Agent 1: 遊戲開發者
game_developer = Agent(
    role='資深 Python 遊戲開發者',
    goal='使用 Python 和 Pygame 函式庫,撰寫一個功能完整的貪吃蛇遊戲。',
    backstory="""您是一位專精於 Pygame 的資深開發者,
    擅長撰寫乾淨、可執行且有趣的 2D 遊戲。
    您需要確保程式碼是單一檔案、包含所有必要的邏輯 (遊戲迴圈、控制、碰撞檢測、計分)。""",
    verbose=True,
    allow_delegation=False,
    llm=ollama_llm
)

# Agent 2: QA 測試工程師
qa_tester = Agent(
    role='軟體品保 (QA) 工程師',
    goal='嚴格測試開發者提供的 Pygame 程式碼,確保其可以被執行且沒有立即性的錯誤。請使用繁體中文撰寫測試報告。',
    backstory="""您是個注重細節的 QA 測試者。您的唯一任務是使用 'code_execution_tool'
    來運行程式碼。你必須根據工具的回報來判斷程式碼是否成功啟動。
    如果失敗,你必須提供完整的錯誤訊息。
    重要:您必須使用繁體中文撰寫所有測試報告和結論。""",
    verbose=True,
    allow_delegation=False,
    tools=[code_executor],
    llm=ollama_llm,
)

# Agent 3: Debug 工程師
debug_engineer = Agent(
    role='Debug 除錯專家',
    goal='分析測試失敗的程式碼,找出錯誤原因並修正它。',
    backstory="""您是一位經驗豐富的 Debug 專家,擅長閱讀錯誤訊息並快速定位問題。
    當 QA 回報程式碼執行失敗時,您會仔細分析錯誤訊息,找出根本原因,
    並撰寫修正後的完整程式碼。您總是能夠解決各種 Python 和 Pygame 相關的錯誤。""",
    verbose=True,
    allow_delegation=False,
    llm=ollama_llm
)

# ----------------------------
# 5. 主要執行邏輯 (加入迭代機制)
# ----------------------------

MAX_ITERATIONS = 100  # 最多嘗試 5 次

# 用來記錄每次迭代的歷程
iteration_history = []


def run_development_cycle():
    """
    執行開發-測試-除錯循環,直到測試通過或達到最大迭代次數
    """

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n{'='*60}")
        print(f"🔄 第 {iteration} 次迭代開始")
        print(f"{'='*60}\n")

        # 根據是第幾次迭代,決定開發任務的描述
        if iteration == 1:
            # 第一次: 從零開始開發
            develop_description = """撰寫一個完整的、單一檔案的貪吃蛇遊戲。
            - 使用 Python 和 Pygame。
            - 遊戲視窗大小應為 600x400。
            - 包含蛇的移動 (上下左右鍵)、食物的隨機生成、吃到食物後蛇身變長、撞到牆壁或自己時遊戲結束。
            - 必須包含一個主遊戲迴圈 (game loop)。
            - 確保程式碼正確初始化 Pygame,並正確處理事件。
            - **你的最終輸出必須只有完整的 Python 程式碼,沒有其他多餘的文字或解釋。**
            """
            current_agent = game_developer
        else:
            # 第二次以後: 根據錯誤訊息進行除錯
            develop_description = f"""根據上一次測試的錯誤報告,修正貪吃蛇遊戲的程式碼。
            
            請仔細閱讀錯誤訊息,找出問題所在,並撰寫修正後的完整程式碼。
            常見問題包括:
            - Pygame 初始化錯誤
            - 變數未定義
            - 邏輯錯誤
            - 語法錯誤
            
            **你的最終輸出必須只有修正後的完整 Python 程式碼,沒有其他多餘的文字或解釋。**
            """
            current_agent = debug_engineer

        # 建立開發/除錯任務
        develop_task = Task(
            description=develop_description,
            expected_output='一個包含完整、可執行的貪吃蛇遊戲的 Python 程式碼字串。',
            agent=current_agent
        )

        # 建立測試任務
        test_task = Task(
            description="""從開發者那裡取得貪吃蛇的 Python 程式碼。
            使用 'code_execution_tool' 來執行這段程式碼。
            根據工具的回報,使用繁體中文撰寫一份測試報告。
            
            報告格式要求:
            - 必須使用繁體中文
            - 第一行必須明確標示: 測試結果: 成功 或 測試結果: 失敗
            - 如果工具回報包含 "執行成功",請用中文說明遊戲成功運行
            - 如果工具回報包含 "執行失敗" 或任何錯誤,請用中文說明失敗原因,並附上完整的錯誤訊息
            - 報告要清晰、專業
            
            範例格式:
            測試結果: 成功
            詳細說明: 貪吃蛇遊戲成功啟動並運行 10 秒,遊戲迴圈正常運作。
            """,
            expected_output='一份繁體中文測試報告,明確說明程式碼是否成功執行。',
            agent=qa_tester,
            context=[develop_task]
        )

        # 建立並執行 Crew
        game_crew = Crew(
            agents=[current_agent, qa_tester],
            tasks=[develop_task, test_task],
            process=Process.sequential,
            verbose=True
        )

        print(f"🚀 開始執行第 {iteration} 次開發與測試...")
        result = game_crew.kickoff()

        print(f"\n{'='*60}")
        print(f"📋 第 {iteration} 次迭代測試報告:")
        print(f"{'='*60}")
        print(result)
        print(f"{'='*60}\n")

        # 記錄這次迭代的結果
        iteration_record = {
            'iteration': iteration,
            'agent': '初始開發者' if iteration == 1 else 'Debug 除錯專家',
            'result': str(result),
            'success': False
        }

        # 檢查測試是否通過
        result_str = str(result).lower()
        if "測試結果: 成功" in str(result) or "執行成功" in result_str or "成功運行" in result_str:
            iteration_record['success'] = True
            iteration_history.append(iteration_record)

            print(f"\n✅ 成功! 在第 {iteration} 次迭代中產生了可運行的貪吃蛇遊戲!")

            # 保存成功的程式碼到 snake_game.py
            if code_executor.last_tested_code:
                try:
                    with open("snake_game.py", "w", encoding="utf-8") as f:
                        f.write(code_executor.last_tested_code)
                    print(f"💾 成功的程式碼已保存到: snake_game.py")
                except Exception as e:
                    print(f"⚠️  保存檔案時發生錯誤: {e}")

            print(f"\n最終測試報告:\n{result}")
            return True, result
        else:
            iteration_history.append(iteration_record)
            print(f"\n❌ 第 {iteration} 次測試失敗,準備進行下一次迭代...")
            if iteration == MAX_ITERATIONS:
                print(f"\n⚠️  已達到最大迭代次數 ({MAX_ITERATIONS} 次),仍未成功。")
                print(f"\n最後測試報告:\n{result}")
                return False, result

    return False, "未知錯誤"


def generate_summary_report():
    """
    產生開發總結報告
    """
    summary_agent = Agent(
        role='專案總結分析師',
        goal='分析整個開發過程,總結所有遇到的錯誤、修改方案,並提供開發心得。',
        backstory="""您是一位經驗豐富的專案分析師,擅長從開發歷程中提取有價值的見解。
        您會仔細分析每次迭代的錯誤訊息,歸納問題類型,說明解決方案,
        並提供專業的開發心得和建議。您的報告必須使用繁體中文撰寫,內容要清晰、有條理。""",
        verbose=True,
        allow_delegation=False,
        llm=ollama_llm
    )

    # 準備歷程資料
    history_text = ""
    for i, record in enumerate(iteration_history, 1):
        history_text += f"\n### 第 {record['iteration']} 次迭代\n"
        history_text += f"負責人員: {record['agent']}\n"
        history_text += f"測試結果: {'✅ 成功' if record['success'] else '❌ 失敗'}\n"
        history_text += f"詳細報告:\n{record['result']}\n"
        history_text += "-" * 50 + "\n"

    summary_task = Task(
        description=f"""請根據以下開發歷程,撰寫一份完整的專案總結報告。

開發歷程記錄:
{history_text}

報告必須包含以下章節 (使用繁體中文):

# 🎮 貪吃蛇遊戲開發專案總結報告

## 📊 專案概況
- 總迭代次數: {len(iteration_history)}
- 最終結果: [成功/失敗]
- 使用技術: Python + Pygame

## 🐛 錯誤分析與修正歷程

請逐一列出每次迭代遇到的問題:

### 第 N 次迭代
- **遇到的錯誤**: [具體描述錯誤訊息和問題]
- **錯誤類型**: [例如: 語法錯誤、邏輯錯誤、初始化問題等]
- **修正方案**: [說明如何解決這個問題]
- **修正結果**: [成功/失敗]

(重複以上格式,直到所有迭代都分析完畢)

## 🔍 問題統計與分類

請統計並分類所有遇到的問題:
- 語法錯誤: X 次
- Pygame 初始化問題: X 次
- 邏輯錯誤: X 次
- 其他: X 次

## 💡 開發心得與建議

請提供以下內容:

### 成功關鍵因素
- [列出促成專案成功的關鍵因素]

### 常見陷阱
- [列出開發過程中容易犯的錯誤]

### 改進建議
- [對未來類似專案的建議]

### 技術學習重點
- [從這次開發中學到的技術要點]

## 🎯 結論

[用 2-3 段話總結整個開發經驗]

---
報告完成日期: {__import__('datetime').datetime.now().strftime('%Y年%m月%d日')}
        """,
        expected_output='一份完整的繁體中文專案總結報告,包含錯誤分析、修正歷程和開發心得。',
        agent=summary_agent
    )

    summary_crew = Crew(
        agents=[summary_agent],
        tasks=[summary_task],
        process=Process.sequential,
        verbose=True
    )

    print("\n" + "="*60)
    print("📝 正在產生專案總結報告...")
    print("="*60 + "\n")

    summary_result = summary_crew.kickoff()

    # 將報告儲存為檔案
    try:
        with open("開發總結報告.md", "w", encoding="utf-8") as f:
            f.write(str(summary_result))
        print("\n💾 總結報告已保存到: 開發總結報告.md\n")
    except Exception as e:
        print(f"\n⚠️  保存報告時發生錯誤: {e}\n")

    return summary_result


# ----------------------------
# 7. 啟動任務！
# ----------------------------
if __name__ == "__main__":
    print("🎮 貪吃蛇遊戲自動開發系統啟動!")
    print("📌 系統會自動進行開發-測試-除錯循環,直到產生可運行的遊戲\n")

    success, final_report = run_development_cycle()

    print("\n" + "="*60)
    if success:
        print("🎉 任務完成! 已成功產生可運行的貪吃蛇遊戲!")
        print("📁 檔案位置: snake_game.py")
        print("▶️  執行指令: python snake_game.py")
    else:
        print("😞 任務失敗: 在最大迭代次數內未能產生可運行的遊戲")
    print("="*60)

    # 產生總結報告
    print("\n\n" + "🔷"*30)
    print("開始產生開發歷程總結報告")
    print("🔷"*30 + "\n")

    summary = generate_summary_report()

    print("\n" + "="*60)
    print("📊 專案總結報告")
    print("="*60)
    print(summary)
    print("="*60)
