import os
from openai import OpenAI
from dotenv import load_dotenv

## 代码结构设计
'''
模型选择与配置：模型提供商(provider)--模型
    OpenAI:
        gpt-4o
        gpt-5
        ...
    Google:
        gemini-2.5-flash
    DeepSeek:
        deepseek R1
        deepseek V3
    Tongyi:
        QWen-plus
        QWen-flash

'''

## 从环境变量中获取模型API密钥
load_dotenv()


## DeepSeek模型
# API_KEY_DeepSeek=os.getenv('API_KEY_DeepSeek')
# if not API_KEY_DeepSeek:
#     raise ValueError("DEEPSEEK_API_KEY 未在环境变量中找到，请检查 .env 文件")

# client = OpenAI(
#     api_key=API_KEY_DeepSeek,
#     base_url="https://api.deepseek.com")

# response = client.chat.completions.create(
#     model="deepseek-chat",
#     messages=[
#         {"role": "system", "content": "你是一个专业的眼科医生"}, 
#         {"role": "user", "content": "请介绍一下白内障疾病"},
#     ],
#     stream=False
# )

# print(response.choices[0].message.content)

## QWen模型
# API_KEY_QWen=os.getenv('API_KEY_QWen')
# if not API_KEY_QWen:
#     raise ValueError("API_KEY_QWen 未在环境变量中找到，请检查 .env 文件")

# client = OpenAI(
#     api_key=API_KEY_QWen,
#     base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

# response = client.chat.completions.create(
#     model="qwen-plus",
#     messages=[
#         {"role": "system", "content": "你是一个专业的眼科医生"}, 
#         {"role": "user", "content": "请介绍一下白内障疾病"},
#     ],
#     stream=False
# )

# print(response.choices[0].message.content)


## GPT模型
API_KEY=os.getenv('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY 未在环境变量中找到，请检查 .env 文件")


# client = OpenAI(
#     api_key=API_KEY,
#     base_url="https://sg.uiuiapi.com/v1"
# )

# response = client.chat.completions.create(
#     model="gpt-4o",
#     messages=[
#         {"role": "system", "content": "你是一个专业的眼科医生"}, 
#         {"role": "user", "content": "请介绍一下白内障疾病"},
#     ]
# )

# print(response)
# print(response.choices[0].message.content)


## Gemini模型
client = OpenAI(
    api_key=API_KEY,
    base_url="https://sg.uiuiapi.com/v1"
)

response = client.chat.completions.create(
    model="gemini-2.0-flash",
    messages=[
        {"role": "system", "content": "你是一个专业的眼科医生"}, 
        {"role": "user", "content": "请介绍一下白内障疾病"},
    ],
    stream=False
)

print(response.choices[0].message.content)
