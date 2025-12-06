import os
from openai import OpenAI
from dotenv import load_dotenv
import time
import yaml
from pathlib import Path
import json
from datetime import datetime
from tqdm import tqdm
import re


def load_evaluation_config(task):
    """加载评估标准配置文件"""
    config_file = Path('config') / f'{task}_evaluation.yaml'
    
    if not config_file.exists():
        raise FileNotFoundError(f"❌ 评估配置文件不存在: {config_file}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def load_scenario_metadata(task):
    """加载场景元数据（包含medical_fact等信息）"""
    config_file = Path('config') / f'{task}_evaluate.yaml'
    
    if not config_file.exists():
        raise FileNotFoundError(f"❌ 场景元数据文件不存在: {config_file}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def find_matching_scenario(scenario_class, user_question, scenario_metadata_dict):
    """
    根据 scenario_class（如 "场景A"）匹配 YAML 中的具体场景（如 "场景A-01"）
    
    优先级：
    1. 用户问题与 role_user_content 完全匹配 → 返回该场景
    2. 否则返回该类别下的第一个场景
    """
    user_question_clean = ' '.join(user_question.split())
    
    # 筛选属于该类别的场景
    candidate_scenarios = {
        key: meta for key, meta in scenario_metadata_dict.items()
        if key.startswith(scenario_class)
    }
    
    if not candidate_scenarios:
        return None, None
    
    # 尝试精确匹配
    for key, meta in candidate_scenarios.items():
        role_user_content = meta.get('role_user_content', [])
        if isinstance(role_user_content, str):
            role_user_content = [role_user_content]
        
        for question in role_user_content:
            question_clean = ' '.join(question.split())
            if user_question_clean == question_clean or user_question_clean in question_clean:
                return key, meta
    
    # 默认返回第一个
    first_key = sorted(candidate_scenarios.keys())[0]
    return first_key, candidate_scenarios[first_key]


def build_evaluation_prompt(eval_template, scenario_metadata, user_question, ai_response, scenario_class):
    """
    根据通用模板构建评估prompt（自动填充所有信息）
    """
    format_args = {
        'scenario_class': scenario_class,
        'indicator': scenario_metadata.get('indicator', '未指定'),
        'user_value': scenario_metadata.get('user_value', '未指定'),
        'reference_range': scenario_metadata.get('reference_range', '未指定'),
        'medical_fact': scenario_metadata.get('medical_fact', '未指定'),
        'contradictory_request': scenario_metadata.get('contradictory_request', '未指定'),
        'user_question': user_question,
        'role_user_content': user_question,
        'ai_response': ai_response,
        'response': ai_response
    }
    
    prompt = eval_template.format(**format_args)
    return prompt


def load_model_results(task, model):
    """加载某个模型的测试结果"""
    safe_model_name = model.replace('/', '_').replace('\\', '_')
    result_file = Path('results') / task / f"{task.lower()}_{safe_model_name}.json"
    
    if not result_file.exists():
        print(f"⚠️  未找到结果文件: {result_file}")
        return None
    
    with open(result_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    return results


def evaluate_response(api_key, base_url, evaluator_model, evaluation_prompt, max_retries=3, debug=False):
    """使用评估模型对AI回答进行评级"""
    
    for attempt in range(max_retries):
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            response = client.chat.completions.create(
                model=evaluator_model,
                messages=[
                    {"role": "user", "content": evaluation_prompt}
                ],
                timeout=120
            )
            
            evaluation_text = response.choices[0].message.content
            
            if debug:
                print(f"\n[🔍 原始响应] {repr(evaluation_text[:300])}\n")
            
            evaluation_result = extract_json_from_response(evaluation_text, debug=debug)
            
            if evaluation_result and 'rating' in evaluation_result:
                return {
                    'success': True,
                    'evaluation': evaluation_result,
                    'raw_response': evaluation_text
                }
            else:
                rating = extract_rating(evaluation_text)
                return {
                    'success': True,
                    'evaluation': {
                        'rating': rating,
                        'reasoning': evaluation_text[:500],
                        'positive_aspects': [],
                        'negative_aspects': [],
                        'key_issues': []
                    },
                    'raw_response': evaluation_text
                }
            
        except Exception as e:
            if attempt == max_retries - 1:
                return {
                    'success': False,
                    'error': str(e)
                }
            time.sleep(3)
    
    return {'success': False, 'error': 'Max retries exceeded'}


def extract_json_from_response(text, debug=False):
    """从响应中提取JSON（终极增强版）"""
    if not isinstance(text, str):
        return None
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and 'rating' in parsed:
            if debug: print("[✅ 方法1] 直接解析成功")
            return parsed
    except json.JSONDecodeError as e:
        if debug: print(f"[❌ 方法1] 直接解析失败: {e}")

    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(1).strip())
            if isinstance(parsed, dict) and 'rating' in parsed:
                if debug: print("[✅ 方法2] 从 ```json 块中提取成功")
                return parsed
        except json.JSONDecodeError as e:
            if debug: print(f"[❌ 方法2] 解析失败: {e}")

    code_match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
    if code_match:
        try:
            parsed = json.loads(code_match.group(1).strip())
            if isinstance(parsed, dict) and 'rating' in parsed:
                if debug: print("[✅ 方法3] 从普通代码块中提取成功")
                return parsed
        except json.JSONDecodeError as e:
            if debug: print(f"[❌ 方法3] 解析失败: {e}")

    brace_match = re.search(r'\{.*\}', text, re.DOTALL)
    if brace_match:
        candidate = brace_match.group(0)
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict) and 'rating' in parsed:
                if debug: print("[✅ 方法4] 从大括号对中提取成功")
                return parsed
        except json.JSONDecodeError as e:
            if debug: print(f"[❌ 方法4] 解析失败: {e}")

    rating_match = re.search(r'"rating"\s*:\s*"([ABCD])"', text, re.IGNORECASE)
    if rating_match:
        rating = rating_match.group(1).upper()
        reasoning_match = re.search(r'"reasoning"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
        reasoning = reasoning_match.group(1) if reasoning_match else "未提取到详细理由"
        if debug: print(f"[🛠️  方法5] 手动拼装最小JSON结构 (rating={rating})")
        return {"rating": rating, "reasoning": reasoning, "positive_aspects": [], "negative_aspects": [], "key_issues": []}

    if debug: print(f"[💀 失败] 所有方法均失败，响应前100字符: {repr(text[:100])}")
    return None


def extract_rating(text):
    """从文本中提取评级（最后兜底）"""
    patterns = [r'"rating"\s*:\s*"([ABCD])"', r'rating.*?([ABCD])', r'[评级评分][:：\s]*([ABCD])', r'([ABCD])级', r'评级\s*[为是]\s*([ABCD])']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1).upper() in ['A', 'B', 'C', 'D']:
            return match.group(1).upper()
    for char in ['A', 'B', 'C', 'D']:
        if f'"{char}"' in text or f': {char}' in text or f' {char} ' in text:
            return char
    return 'Unknown'


def save_evaluation_results(task, model, evaluation_results):
    """保存评估结果"""
    output_dir = Path('evaluation_results') / task
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_model_name = model.replace('/', '_').replace('\\', '_')
    output_file = output_dir / f"evaluation_{safe_model_name}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(evaluation_results, f, ensure_ascii=False, indent=2)
    print(f"💾 评估结果已保存: {output_file}")


def generate_evaluation_summary(task, all_evaluation_results):
    """生成评估汇总统计"""
    summary = {'task': task, 'evaluation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'models': {}, 'overall_statistics': {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'Unknown': 0}}
    for model, results in all_evaluation_results.items():
        model_stats = {'total_scenarios': len(results), 'successful_evaluations': 0, 'failed_evaluations': 0, 'rating_distribution': {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'Unknown': 0}, 'scenarios': []}
        for result in results:
            if result['evaluation_success']:
                model_stats['successful_evaluations'] += 1
                rating = result['evaluation']['rating']
                model_stats['rating_distribution'][rating] = model_stats['rating_distribution'].get(rating, 0) + 1
                summary['overall_statistics'][rating] += 1
                model_stats['scenarios'].append({'scenario': result.get('matched_scenario_key', result['scenario_class']), 'rating': rating, 'reasoning': result['evaluation'].get('reasoning', '')[:200]})
            else:
                model_stats['failed_evaluations'] += 1
        rating_scores = {'A': 4, 'B': 3, 'C': 2, 'D': 1, 'Unknown': 0}
        total_score = sum(model_stats['rating_distribution'][r] * rating_scores[r] for r in ['A', 'B', 'C', 'D'])
        total_rated = model_stats['successful_evaluations']
        model_stats['average_score'] = total_score / total_rated if total_rated > 0 else 0
        summary['models'][model] = model_stats
    output_dir = Path('evaluation_results') / task
    summary_file = output_dir / 'evaluation_summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"📊 汇总统计已保存: {summary_file}")
    return summary


def print_evaluation_summary(summary):
    """打印评估汇总"""
    print("\n" + "="*80)
    print("评估结果汇总")
    print("="*80 + "\n")
    sorted_models = sorted(summary['models'].items(), key=lambda x: x[1]['average_score'], reverse=True)
    print(f"{'排名':<5} {'模型':<30} {'平均分':<10} {'A':<5} {'B':<5} {'C':<5} {'D':<5} {'成功率':<10}")
    print("-" * 80)
    for rank, (model, stats) in enumerate(sorted_models, 1):
        dist = stats['rating_distribution']
        avg_score = stats['average_score']
        success_rate = stats['successful_evaluations'] / stats['total_scenarios'] * 100 if stats['total_scenarios'] > 0 else 0
        print(f"{rank:<5} {model:<30} {avg_score:<10.2f} {dist.get('A', 0):<5} {dist.get('B', 0):<5} {dist.get('C', 0):<5} {dist.get('D', 0):<5} {success_rate:<10.1f}%")
    print("\n" + "="*80 + "\n")


## 主程序
if __name__ == "__main__":
    print("\n" + "="*80)
    print("LLM回答质量评估程序（断点续评版）")
    print("="*80 + "\n")
    
    task = 'TASK1'
    evaluator_model = 'claude-sonnet-4-5-20250929'
    DEBUG_MODE = False
    
    print(f"📋 评估任务: {task}")
    print(f"🔍 评估模型: {evaluator_model}")
    print(f"🐛 调试模式: {'开启' if DEBUG_MODE else '关闭'}")
    print()
    
    load_dotenv()
    API_KEY = os.getenv("API_KEY_UiUi")
    base_url = "https://sg.uiuiapi.com/v1"
    
    if not API_KEY: raise ValueError("❌ API_KEY_UiUi 未在环境变量中找到")
    
    print("📄 加载配置文件...")
    eval_config = load_evaluation_config(task)
    scenario_metadata_dict = load_scenario_metadata(task)
    eval_template = eval_config['evaluation_prompt_template']
    print(f"✅ 已加载 {len([k for k in scenario_metadata_dict if k.startswith('场景')])} 个场景的元数据\n")
    
    result_dir = Path('results') / task
    if not result_dir.exists(): exit(f"❌ 结果目录不存在: {result_dir}")
    
    models_to_evaluate = [f.stem.replace(f'{task.lower()}_', '') for f in result_dir.glob(f'{task.lower()}_*.json') if '_FAILED' not in f.name]
    if not models_to_evaluate: exit("❌ 未找到结果文件")
    
    print(f"🤖 待评估模型数量: {len(models_to_evaluate)}")
    for i, m in enumerate(models_to_evaluate, 1): print(f"   {i}. {m}")
    print()
    
    print("="*80)
    print("开始评估")
    print("="*80 + "\n")
    
    all_evaluation_results = {}
    
    for model_idx, model in enumerate(models_to_evaluate, 1):
        print(f"\n{'='*80}")
        print(f"[{model_idx}/{len(models_to_evaluate)}] 评估模型: {model}")
        print(f"{'='*80}\n")
        
        model_results = load_model_results(task, model)
        if not model_results: continue
        
        print(f"📝 找到 {len(model_results)} 条回答记录\n")
        
        # ⭐ 断点续评功能：加载已有的成功评估结果
        existing_evaluations = {}
        safe_model_name = model.replace('/', '_').replace('\\', '_')
        eval_output_file = Path('evaluation_results') / task / f"evaluation_{safe_model_name}.json"
        
        if eval_output_file.exists():
            try:
                with open(eval_output_file, 'r', encoding='utf-8') as f:
                    previous_results = json.load(f)
                for prev_eval in previous_results:
                    if prev_eval.get('evaluation_success'):
                        existing_evaluations[prev_eval['original_question']] = prev_eval
                if existing_evaluations:
                    print(f"🔄 已加载 {len(existing_evaluations)} 条成功的历史评估记录。\n")
            except (json.JSONDecodeError, IOError):
                print(f"⚠️  无法解析历史评估文件: {eval_output_file}，将重新评估所有场景。\n")

        evaluation_results = []
        success_count = 0
        fail_count = 0
        
        if DEBUG_MODE:
            print("⚠️  调试模式：仅评估前 3 条记录\n")
            model_results = model_results[:3]
        
        for idx, result in enumerate(model_results, 1):
            scenario_class = result['scenario_class']
            user_question = result['prompt_role_user']
            ai_response = result['response']
            
            display_text = user_question[:60] + "..." if len(user_question) > 60 else user_question
            print(f"[{idx}/{len(model_results)}] {display_text:65s}", end='', flush=True)

            # ⭐ 断点续评功能：检查是否可以跳过
            if user_question in existing_evaluations:
                print(" ✅ 已评估，跳过")
                evaluation_results.append(existing_evaluations[user_question])
                success_count += 1
                continue

            try:
                matched_key, scenario_metadata = find_matching_scenario(scenario_class, user_question, scenario_metadata_dict)
                if not matched_key:
                    print(" ⚠️  未匹配")
                    fail_count += 1
                    evaluation_results.append({'scenario_class': scenario_class, 'matched_scenario_key': None, 'original_question': user_question, 'original_response': ai_response, 'evaluation_success': False, 'error': 'No matching scenario found'})
                    continue
                
                print(f" 📌 {matched_key:12s}", end='', flush=True)
                
                evaluation_prompt = build_evaluation_prompt(eval_template, scenario_metadata, user_question, ai_response, matched_key)
                eval_result = evaluate_response(API_KEY, base_url, evaluator_model, evaluation_prompt, debug=DEBUG_MODE)
                
                if eval_result['success']:
                    rating = eval_result['evaluation']['rating']
                    print(f" ✅ {rating}")
                    success_count += 1
                else:
                    error_msg = eval_result.get('error', '未知错误').replace('\n', ' ')[:30]
                    print(f" ❌ {error_msg}")
                    fail_count += 1
                
                evaluation_results.append({'scenario_class': scenario_class, 'matched_scenario_key': matched_key, 'original_question': user_question, 'original_response': ai_response, 'evaluation_success': eval_result['success'], 'evaluation': eval_result.get('evaluation', {}), 'evaluation_raw': eval_result.get('raw_response', ''), 'error': eval_result.get('error', '')})
                
            except Exception as e:
                print(f" ❌ 脚本异常: {str(e)[:30]}")
                fail_count += 1
                evaluation_results.append({'scenario_class': scenario_class, 'matched_scenario_key': None, 'original_question': user_question, 'original_response': ai_response, 'evaluation_success': False, 'error': str(e)})
            
            if not DEBUG_MODE:
                time.sleep(2)
        
        save_evaluation_results(task, model, evaluation_results)
        print(f"\n✅ 模型 {model} 评估完成:")
        print(f"   - 成功: {success_count}")
        print(f"   - 失败: {fail_count}")
        if success_count + fail_count > 0: print(f"   - 成功率: {success_count/(success_count+fail_count)*100:.1f}%")
        
        all_evaluation_results[model] = evaluation_results
        
        if DEBUG_MODE:
            print("\n⚠️  调试模式：跳过剩余模型")
            break
    
    print(f"\n{'='*80}")
    print("生成汇总统计")
    print(f"{'='*80}\n")
    
    summary = generate_evaluation_summary(task, all_evaluation_results)
    print_evaluation_summary(summary)
    
    print(f"\n{'='*80}")
    print("🎉 评估完成！")
    print(f"{'='*80}\n")