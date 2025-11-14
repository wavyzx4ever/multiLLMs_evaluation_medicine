import os
from openai import OpenAI
from dotenv import load_dotenv
import time
from typing import List, Dict
import yaml
from pathlib import Path



## 函数封装
def LLM_request(api_key, base_url, model, messages):
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        # response = client.chat.completions.create(model=model, messages=messages, stream=False, timeout=30)
        response = client.chat.completions.create(model=model, messages=messages, stream=False)

        return {
            "model": model,
            "prompt": messages,
            "response": response.choices[0].message.content,
            "success": True
        }
    except Exception as e:
        print(f"LLM请求失败: {model} - {messages} - 错误: {str(e)}")
        return {
            "success": False
        }



## API配置
load_dotenv()   # 从环境变量中获取模型API密钥
API_KEY_UiUi = os.getenv("API_KEY_UiUi")
if not API_KEY_UiUi:
    raise ValueError("API_KEY_UiUi 未在环境变量中找到")


## 站点网址
base_url="https://sg.uiuiapi.com/v1"


## 模型列表
# model_list = ['gpt-5', 'claude-3', 'gemini-2.5', 'grok-3', 'deepseek-r1', 'qwen-plus', 'kimi-k2', 'doubao-seed', 'glm-4.6-thinking']
model_list = [ 'qwen-plus']


## 任务提示词选择
'''
任务名称：
TASK_1: 交互鲁棒性评估
TASK_2: xxxxxxxxx评估
TASK_3: xxxxxxxxx评估
TASK_4: xxxxxxxxx评估
TASK_5: xxxxxxxxx评估
'''
target_task = 'TASK1'   # ??

# find 任务提示词配置文件
current_file_path = Path(__file__).resolve()
project_root_path = current_file_path.parent
task_promt_filename = f'{target_task}_promts.yaml'
config_file_path = project_root_path / 'config' / task_promt_filename
print(config_file_path)
if not os.path.exists(config_file_path):
    raise FileNotFoundError(f"配置文件不存在: {config_file_path}")

with open(config_file_path, 'r', encoding='utf-8') as f:
    task_config = yaml.safe_load(f) or {}

# 验证配置结构
if not isinstance(task_config, dict):
    raise ValueError("配置文件格式错误，应为字典结构")

## !! TODO：选择更灵活的循环方式，避免每次执行都全部任务--场景--提示词--模型都循环一边，需要每次按需选择(参考昨天的元宝给出的代码)
for model in model_list:
    for scenario_name, scenario_config in task_config.items():
        role_system_content = scenario_config['role_system_content']
        role_user_content = scenario_config['role_user_content']
        for promt in role_user_content:
            messages=[
                {"role": "system", "content": role_system_content}, 
                {"role": "user", "content": promt}
            ]
            print(messages)

            # TODO: 将messages传递给前面的LLM访问请求函数
            LLM_answer = LLM_request(api_key=API_KEY_UiUi, base_url=base_url, model=model, messages=messages)
            print(LLM_answer)

            time.sleep(2)
