import os
from openai import OpenAI
from dotenv import load_dotenv
import time
from typing import List, Dict
import yaml
from pathlib import Path
import json
from datetime import datetime
import pypandoc



## 函数封装
# 访问LLM
def LLM_request(api_key, base_url, model, scenario_class, messages):
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        # response = client.chat.completions.create(model=model, messages=messages, stream=False, timeout=30)
        response = client.chat.completions.create(model=model, messages=messages, stream=False)

        return {
            'model': model,
            'scenario_class': scenario_class,
            'prompt': messages,
            'response': response.choices[0].message.content,
            'success': True
        }
    except Exception as e:
        print(f"LLM请求失败: {model} - {messages} - 错误: {str(e)}")
        return {
            'success': False
        }

# 保存LLM输出结果到.json文件
def LLM_results_save(task:str, model:str, LLM_answers):
    results = []
    for answer in LLM_answers:
        record = {
            'scenario_class': answer.get('scenario_class','') if answer.get('scenario_class') else '',
            'prompt_role_system': answer.get('prompt',[])[0].get('content','') if answer.get('prompt') else '',
            'prompt_role_user': answer.get('prompt',[])[1].get('content','') if answer.get('prompt') else '',
            'response': answer.get('response','') if answer.get('response') else '',
            'timestamp': datetime.now().strftime('%Y-%m-%d-%H:%M')
        }
        results.append(record)

    result_file_name = task.lower() + '_' + model + '.json'
    result_file_path = 'results/TASK1'
    with open(os.path.join(result_file_path, result_file_name), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def markdown_to_word(markdown_text, output_path):
    """Markdown转Word"""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        output = pypandoc.convert_text(
            markdown_text, 
            'docx', 
            format='md', 
            outputfile=output_path
        )
        print(f"✓ Word文档已生成: {output_path}")
        return True
    except Exception as e:
        print(f"✗ 转换失败: {e}")
        return False


def get_combined_markdown_content(data):
    """创建包含所有场景的合并Markdown内容"""
    
    combined_content = f"""# AI对话记录汇总报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**总记录数**: {len(data)}

---
"""
    
    for i, item in enumerate(data, 1):
        scenario_class = item.get('scenario_class', f'场景_{i}')
        system_prompt = item.get('prompt_role_system', '')
        user_prompt = item.get('prompt_role_user', '')
        response_content = item.get('response', '')
        timestamp = item.get('timestamp', '')
        
        # 为每个场景添加分隔符和标题
        combined_content += f"""
## {i}. {scenario_class}

### 基本信息
- **生成时间**: {timestamp}
- **场景分类**: {scenario_class}
- **记录编号**: 第{i}条

### 对话设置
**系统角色设定**:
{system_prompt}

**用户问题**:
{user_prompt}

### AI回复内容
{response_content}

---
"""
    
    combined_content += f"\n\n*文档生成完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
    return combined_content

def convert_json_to_single_word(json_file_path):
    """将JSON文件的所有内容合并到一个Word文件中"""
    
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📁 找到 {len(data)} 条记录")
    
    # 生成与JSON文件平行的Word文件路径
    json_dir = os.path.dirname(json_file_path)
    json_filename = os.path.basename(json_file_path)
    word_filename = os.path.splitext(json_filename)[0] + '.docx'
    output_path = os.path.join(json_dir, word_filename)
    
    # 创建合并的Markdown内容
    combined_markdown = get_combined_markdown_content(data)
    
    # 转换为Word
    if markdown_to_word(combined_markdown, output_path):
        print(f"✅ 成功生成合并Word文件: {output_path}")
        return True
    else:
        print(f"❌ 生成Word文件失败")
        return False


## 程序入口
if __name__ == "__main__":


    ## 任务提示词选择
    '''
    任务名称：
    TASK_1: 交互鲁棒性评估
    TASK_2: xxxxxxxxx评估
    TASK_3: xxxxxxxxx评估
    TASK_4: xxxxxxxxx评估
    TASK_5: xxxxxxxxx评估
    '''
    target_task = 'TASK1'         # ?? 选择一个任务


    ## 模型列表
    # model_list = ['gpt-5', 'claude-3', 'gemini-2.5', 'grok-3', 'deepseek-r1', 'qwen-plus', 'kimi-k2', 'doubao-seed', 'glm-4.6-thinking']
    model_list = [ 'qwen-plus']   # ?? 选择一个或多个需要执行的LLM


    ## API配置
    load_dotenv()   # 从环境变量中获取模型API密钥
    API_KEY_UiUi = os.getenv("API_KEY_UiUi")
    if not API_KEY_UiUi:
        raise ValueError("API_KEY_UiUi 未在环境变量中找到")


    ## 站点网址
    base_url="https://sg.uiuiapi.com/v1"


    ## find 任务提示词配置文件
    current_file_path = Path(__file__).resolve()
    project_root_path = current_file_path.parent
    task_prompt_filename = f'{target_task}_prompts.yaml'
    config_file_path = project_root_path / 'config' / task_prompt_filename
    print(config_file_path)
    if not os.path.exists(config_file_path):
        raise FileNotFoundError(f"配置文件不存在: {config_file_path}")

    with open(config_file_path, 'r', encoding='utf-8') as f:
        task_config = yaml.safe_load(f) or {}

    # 验证配置结构
    if not isinstance(task_config, dict):
        raise ValueError("配置文件格式错误，应为字典结构")


    ## 多层遍历：依次遍历每个prompt
    # for model in model_list:
    #     LLM_answers = []
    #     for scenario_class, scenario_config in task_config.items():
    #         # print(f'scenario_class: {scenario_class}')
    #         role_system_content = scenario_config['role_system_content']
    #         role_user_content = scenario_config['role_user_content']
    #         for prompt in role_user_content:
    #             messages=[
    #                 {"role": "system", "content": role_system_content}, 
    #                 {"role": "user", "content": prompt}
    #             ]
    #             # print(messages)

    #             # 将messages传递给前面的LLM访问请求函数
    #             LLM_answer = LLM_request(api_key=API_KEY_UiUi, base_url=base_url, model=model, scenario_class=scenario_class, messages=messages)

    #             # role_system_content = LLM_answer.get('prompt',[])[0].get('content','') if LLM_answer.get('prompt') else ''
    #             # print(f'role_system_content: {role_system_content}')
    #             # print(LLM_answer)

    #             LLM_answers.append(LLM_answer)

    #             time.sleep(2)

    #     LLM_results_save(task=target_task, model=model, LLM_answers=LLM_answers)


    ## LLM保存结果到json文件后，转换为word文件
    convert_json_to_single_word("results/TASK1/task1_qwen-plus.json")
