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
from tqdm import tqdmß


## 函数封装

def LLM_request(api_key, base_url, model, scenario_class, messages, max_retries=2):
    """访问LLM（增强错误处理+重试+进度显示）"""
    
    for attempt in range(max_retries):
        try:
            if attempt == 0:
                print(f"   📤 {scenario_class[:40]:40s}", end='', flush=True)
            else:
                print(f"   🔄 重试第{attempt}次...", end='', flush=True)
            
            start_time = time.time()
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            # 第一次120秒，重试时180秒
            timeout_value = 120 if attempt == 0 else 180
            
            response = client.chat.completions.create(
                model=model, 
                messages=messages, 
                stream=False,
                timeout=timeout_value
            )
            
            elapsed = time.time() - start_time
            print(f" ✅ {elapsed:.1f}s")

            return {
                'model': model,
                'scenario_class': scenario_class,
                'prompt': messages,
                'response': response.choices[0].message.content,
                'success': True,
                'elapsed_time': elapsed
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_type = type(e).__name__
            error_msg = str(e)
            
            # 判断是否为超时错误
            is_timeout = 'timeout' in error_msg.lower() or error_type == 'Timeout'
            is_last_attempt = (attempt == max_retries - 1)
            
            if is_timeout and not is_last_attempt:
                print(f" ⏱️ 超时({elapsed:.0f}s)")
                continue
            
            # 最后一次失败
            print(f" ❌ {error_type}")
            print(f"      错误: {error_msg[:100]}")
            
            return {
                'model': model,
                'scenario_class': scenario_class,
                'prompt': messages,
                'response': '',
                'success': False,
                'error': error_msg,
                'elapsed_time': elapsed
            }
    
    return {'success': False, 'error': 'Max retries exceeded'}


def LLM_results_save(task:str, model:str, LLM_answers):
    """保存LLM输出结果到.json文件（只保存成功的结果）"""
    results = []
    
    for answer in LLM_answers:
        record = {
            'scenario_class': answer.get('scenario_class',''),
            'prompt_role_system': answer.get('prompt',[])[0].get('content','') if answer.get('prompt') else '',
            'prompt_role_user': answer.get('prompt',[])[1].get('content','') if answer.get('prompt') else '',
            'response': answer.get('response',''),
            'elapsed_time': answer.get('elapsed_time', 0),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        results.append(record)

    # 确保目录存在
    result_file_path = f'results/{task}'
    os.makedirs(result_file_path, exist_ok=True)
    
    # 处理模型名中可能的特殊字符
    safe_model_name = model.replace('/', '_').replace('\\', '_')
    result_file_name = f"{task.lower()}_{safe_model_name}.json"
    full_path = os.path.join(result_file_path, result_file_name)
    
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"💾 结果已保存: {full_path} ({len(results)} 条有效记录)")


def save_failed_scenarios(task:str, model:str, failed_list):
    """保存失败的场景记录"""
    if not failed_list:
        return
    
    result_file_path = f'results/{task}'
    os.makedirs(result_file_path, exist_ok=True)
    
    safe_model_name = model.replace('/', '_').replace('\\', '_')
    failed_file_name = f"{task.lower()}_{safe_model_name}_FAILED.json"
    full_path = os.path.join(result_file_path, failed_file_name)
    
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(failed_list, f, ensure_ascii=False, indent=2)
    
    print(f"⚠️  失败记录已保存: {full_path} ({len(failed_list)} 条)")


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

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**总记录数**: {len(data)}

---
"""
    
    for i, item in enumerate(data, 1):
        scenario_class = item.get('scenario_class', f'场景_{i}')
        system_prompt = item.get('prompt_role_system', '')
        user_prompt = item.get('prompt_role_user', '')
        response_content = item.get('response', '')
        timestamp = item.get('timestamp', '')
        elapsed_time = item.get('elapsed_time', 0)
        
        combined_content += f"""
## {i}. {scenario_class}

### 基本信息
- **生成时间**: {timestamp}
- **响应时间**: {elapsed_time:.1f}秒
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
    
    combined_content += f"\n\n*文档生成完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    return combined_content


def convert_json_to_single_word(json_file_path):
    """将JSON文件的所有内容合并到一个Word文件中"""
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📁 找到 {len(data)} 条记录")
    
    json_dir = os.path.dirname(json_file_path)
    json_filename = os.path.basename(json_file_path)
    word_filename = os.path.splitext(json_filename)[0] + '.docx'
    output_path = os.path.join(json_dir, word_filename)
    
    combined_markdown = get_combined_markdown_content(data)
    
    if markdown_to_word(combined_markdown, output_path):
        print(f"✅ 成功生成合并Word文件: {output_path}")
        return True
    else:
        print(f"❌ 生成Word文件失败")
        return False


def convert_all_json_to_word(task):
    """将某个任务下的所有JSON文件转换为Word（排除FAILED文件）"""
    result_path = f'results/{task}'
    
    if not os.path.exists(result_path):
        print(f"❌ 目录不存在: {result_path}")
        return
    
    # 只转换非FAILED的JSON文件
    json_files = [f for f in Path(result_path).glob('*.json') if '_FAILED' not in f.name]
    
    if not json_files:
        print(f"❌ 未找到JSON文件: {result_path}")
        return
    
    print(f"📁 找到 {len(json_files)} 个JSON文件")
    
    success_count = 0
    fail_count = 0
    
    for json_file in tqdm(json_files, desc="转换进度", ncols=80):
        try:
            if convert_json_to_single_word(str(json_file)):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"❌ 转换失败: {json_file.name} - {e}")
            fail_count += 1
    
    print(f"\n转换完成: 成功 {success_count}, 失败 {fail_count}")


## 程序入口
if __name__ == "__main__":
    
    print("\n" + "="*60)
    print("LLM对比测试程序")
    print("="*60 + "\n")

    ## 任务提示词选择
    '''
    任务名称：
    TASK_1: 交互鲁棒性评估
    TASK_2: xxxxxxxxx评估
    TASK_3: xxxxxxxxx评估
    TASK_4: xxxxxxxxx评估
    TASK_5: xxxxxxxxx评估
    '''
    target_task = 'TASK1'
    print(f"📋 任务: {target_task}")


    ## 模型列表
    model_list = [
        'gpt-5', 'gpt-4o', 'gemini-2.5-flash', 'grok-3', 
        'deepseek-chat', 'qwen-plus', 'kimi-k2-thinking', 
        'doubao-pro-256k', 'glm-4.6'
    ]
    
    print(f"🤖 测试模型数量: {len(model_list)}")
    for i, m in enumerate(model_list, 1):
        print(f"   {i}. {m}")
    print()


    ## API配置
    load_dotenv()
    API_KEY_UiUi = os.getenv("API_KEY_UiUi")
    if not API_KEY_UiUi:
        raise ValueError("❌ API_KEY_UiUi 未在环境变量中找到")


    ## 站点网址
    base_url = "https://sg.uiuiapi.com/v1"


    ## find 任务提示词配置文件
    current_file_path = Path(__file__).resolve()
    project_root_path = current_file_path.parent
    task_prompt_filename = f'{target_task}_prompts.yaml'
    config_file_path = project_root_path / 'config' / task_prompt_filename
    
    print(f"📄 配置文件: {config_file_path}")
    
    if not os.path.exists(config_file_path):
        raise FileNotFoundError(f"❌ 配置文件不存在: {config_file_path}")

    with open(config_file_path, 'r', encoding='utf-8') as f:
        task_config = yaml.safe_load(f) or {}

    if not isinstance(task_config, dict):
        raise ValueError("❌ 配置文件格式错误，应为字典结构")
    
    print(f"📝 场景数量: {len(task_config)}")
    print()


    ## 开始测试
    print("="*60)
    print("开始执行测试")
    print("="*60 + "\n")
    
    overall_start_time = time.time()
    
    # 统计所有模型的总体情况
    overall_stats = {
        'total_success': 0,
        'total_fail': 0,
        'model_stats': {}
    }


    # 多层遍历：依次遍历每个模型
    for model_idx, model in enumerate(model_list, 1):
        print(f"\n{'='*60}")
        print(f"[{model_idx}/{len(model_list)}] 测试模型: {model}")
        print(f"{'='*60}\n")
        
        model_start_time = time.time()
        LLM_answers = []
        failed_scenarios = []  # 记录失败的场景
        success_count = 0
        fail_count = 0
        
        scenarios = list(task_config.items())
        
        for scenario_class, scenario_config in tqdm(scenarios, desc=f"进度", ncols=80):
            role_system_content = scenario_config['role_system_content']
            role_user_content = scenario_config['role_user_content']
            
            for prompt in role_user_content:
                messages = [
                    {"role": "system", "content": role_system_content}, 
                    {"role": "user", "content": prompt}
                ]

                # 调用LLM
                LLM_answer = LLM_request(
                    api_key=API_KEY_UiUi, 
                    base_url=base_url, 
                    model=model, 
                    scenario_class=scenario_class, 
                    messages=messages,
                    max_retries=2
                )

                # 只保存成功的结果
                if LLM_answer.get('success', False):
                    LLM_answers.append(LLM_answer)
                    success_count += 1
                else:
                    fail_count += 1
                    # 记录失败的场景信息
                    failed_scenarios.append({
                        'scenario_class': scenario_class,
                        'role_system_content': role_system_content,
                        'role_user_content': prompt,
                        'error': LLM_answer.get('error', 'Unknown error'),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })

                time.sleep(2)

        # 保存结果
        model_time = time.time() - model_start_time
        
        if LLM_answers:
            LLM_results_save(task=target_task, model=model, LLM_answers=LLM_answers)
            
            # 计算平均响应时间
            avg_time = sum(a.get('elapsed_time', 0) for a in LLM_answers) / len(LLM_answers)
            
            print(f"\n✅ 模型 {model} 完成:")
            print(f"   - 成功: {success_count}")
            print(f"   - 失败: {fail_count}")
            print(f"   - 成功率: {success_count/(success_count+fail_count)*100:.1f}%")
            print(f"   - 总耗时: {model_time:.1f}秒 ({model_time/60:.1f}分钟)")
            print(f"   - 平均响应: {avg_time:.1f}秒")
            
            # 记录统计信息
            overall_stats['model_stats'][model] = {
                'success': success_count,
                'fail': fail_count,
                'success_rate': success_count/(success_count+fail_count)*100,
                'avg_time': avg_time
            }
        else:
            print(f"\n⚠️  模型 {model} 全部失败")
            print(f"   - 失败: {fail_count}")
            
            overall_stats['model_stats'][model] = {
                'success': 0,
                'fail': fail_count,
                'success_rate': 0,
                'avg_time': 0
            }
        
        # 保存失败记录
        if failed_scenarios:
            save_failed_scenarios(task=target_task, model=model, failed_list=failed_scenarios)
        
        # 更新总体统计
        overall_stats['total_success'] += success_count
        overall_stats['total_fail'] += fail_count


    # 总结
    overall_time = time.time() - overall_start_time
    print(f"\n{'='*60}")
    print(f"✅ 所有测试完成！")
    print(f"{'='*60}\n")
    print(f"总体统计:")
    print(f"   - 总成功: {overall_stats['total_success']}")
    print(f"   - 总失败: {overall_stats['total_fail']}")
    print(f"   - 总成功率: {overall_stats['total_success']/(overall_stats['total_success']+overall_stats['total_fail'])*100:.1f}%")
    print(f"   - 总耗时: {overall_time:.1f}秒 ({overall_time/60:.1f}分钟)")
    print()
    
    # 显示各模型成功率排名
    print(f"各模型成功率排名:")
    sorted_models = sorted(overall_stats['model_stats'].items(), 
                          key=lambda x: x[1]['success_rate'], 
                          reverse=True)
    for rank, (model, stats) in enumerate(sorted_models, 1):
        print(f"   {rank}. {model:25s} - {stats['success_rate']:5.1f}% ({stats['success']}/{stats['success']+stats['fail']})")
    
    print(f"\n{'='*60}\n")


    ## 自动转换所有JSON到Word
    print(f"\n{'='*60}")
    print(f"开始转换结果文件")
    print(f"{'='*60}\n")
    
    convert_all_json_to_word(target_task)
    
    
    ## 生成失败场景汇总报告（可选）
    result_path = f'results/{target_task}'
    failed_files = list(Path(result_path).glob('*_FAILED.json'))
    
    if failed_files:
        print(f"\n{'='*60}")
        print(f"失败场景汇总")
        print(f"{'='*60}\n")
        print(f"⚠️  共有 {len(failed_files)} 个模型存在失败场景:")
        
        for failed_file in failed_files:
            with open(failed_file, 'r', encoding='utf-8') as f:
                failed_data = json.load(f)
            
            model_name = failed_file.stem.replace(f'{target_task.lower()}_', '').replace('_FAILED', '')
            print(f"   - {model_name:25s}: {len(failed_data)} 个失败场景")
        
        print(f"\n提示: 使用以下命令重跑失败场景:")
        print(f"   python retry_failed.py {target_task} <模型名>")
        print(f"   或运行: ./retry_all_failed.sh (批量重跑)")
    else:
        print(f"\n🎉 所有场景全部成功，无失败记录！")
    
    
    print(f"\n{'='*60}")
    print(f"🎉 全部流程完成！")
    print(f"{'='*60}\n")