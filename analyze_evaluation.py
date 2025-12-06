import json
from pathlib import Path
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# --- Matplotlib 全局设置 (解决中文乱码和负号问题) ---
plt.rcParams['font.sans-serif'] = ['Heiti TC'] # 或 'SimHei', 'PingFang SC' 等
plt.rcParams['axes.unicode_minus'] = False


def load_evaluation_summary(task):
    """加载评估汇总"""
    summary_file = Path('evaluation_results') / task / 'evaluation_summary.json'
    if not summary_file.exists():
        raise FileNotFoundError(f"❌ 评估汇总文件不存在: {summary_file}")
    with open(summary_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_excel_report(task, summary, output_dir):
    """创建Excel统计报告"""
    overview_data = []
    for model, stats in summary['models'].items():
        total_evaluated = stats.get('successful_evaluations', 0)
        dist = stats.get('rating_distribution', {})
        overview_data.append({
            '模型': model,
            '平均分': stats.get('average_score', 0),
            '成功率': f"{stats.get('successful_evaluations', 0) / stats.get('total_scenarios', 1) * 100:.1f}%",
            'A': dist.get('A', 0), 'B': dist.get('B', 0), 'C': dist.get('C', 0), 'D': dist.get('D', 0),
            'A占比': f"{dist.get('A', 0) / total_evaluated * 100:.1f}%" if total_evaluated > 0 else '0%',
            'AB占比': f"{(dist.get('A', 0) + dist.get('B', 0)) / total_evaluated * 100:.1f}%" if total_evaluated > 0 else '0%'
        })
    df_overview = pd.DataFrame(overview_data).sort_values('平均分', ascending=False)
    
    detailed_data = []
    for model, data in summary['models'].items():
        # 兼容新旧版本的 evaluation_summary.json
        if 'scenarios' not in data:
            full_report_path = Path('evaluation_results') / task / f"evaluation_{model.replace('/', '_')}.json"
            if full_report_path.exists():
                with open(full_report_path, 'r', encoding='utf-8') as f:
                    full_report = json.load(f)
                for res in full_report:
                    if res.get('evaluation_success'):
                        detailed_data.append({
                            '模型': model,
                            '场景': res.get('matched_scenario_key') or res.get('scenario_class'),
                            '评级': res.get('evaluation', {}).get('rating'),
                            '评估理由': res.get('evaluation', {}).get('reasoning', '')
                        })
        else:
             for scenario in data.get('scenarios', []):
                detailed_data.append({'模型': model, '场景': scenario.get('scenario'), '评级': scenario.get('rating'), '评估理由': scenario.get('reasoning')})

    df_detailed = pd.DataFrame(detailed_data)
    
    pivot_data = pd.DataFrame()
    if not df_detailed.empty:
        pivot_data = df_detailed.pivot_table(index='场景', columns='模型', values='评级', aggfunc='first')

    excel_file = output_dir / f'evaluation_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        df_overview.to_excel(writer, sheet_name='总览排名', index=False)
        df_detailed.to_excel(writer, sheet_name='详细评级', index=False)
        if not pivot_data.empty: pivot_data.to_excel(writer, sheet_name='评级对比')
    
    print(f"📊 Excel报告已生成: {excel_file}")


def create_visualizations(task, summary, output_dir):
    """生成并保存可视化图表"""
    df = pd.DataFrame.from_dict(summary['models'], orient='index').sort_values('average_score', ascending=False)
    
    # 1. 平均分对比柱状图
    plt.figure(figsize=(12, 8))
    ax = sns.barplot(x=df.index, y='average_score', data=df, palette='viridis')
    plt.title(f'{task} - 各模型平均分对比', fontsize=16)
    plt.xlabel('模型', fontsize=12)
    plt.ylabel('平均分 (A=4, B=3, C=2, D=1)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    
    # 在柱子上显示数值
    for p in ax.patches:
        ax.annotate(f'{p.get_height():.2f}', (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', fontsize=11, color='black', xytext=(0, 5),
                    textcoords='offset points')
    
    plt.tight_layout()
    avg_score_chart_path = output_dir / 'chart_average_scores.png'
    plt.savefig(avg_score_chart_path, dpi=300)
    print(f"📈 平均分对比图已保存: {avg_score_chart_path}")
    plt.close()

    # 2. 评级分布堆叠柱状图
    ratings_data = []
    for model, stats in summary['models'].items():
        for rating in ['A', 'B', 'C', 'D']:
            ratings_data.append({'模型': model, '评级': rating, '数量': stats['rating_distribution'].get(rating, 0)})
    df_ratings = pd.DataFrame(ratings_data)

    df_pivot = df_ratings.pivot(index='模型', columns='评级', values='数量').loc[df.index][['A', 'B', 'C', 'D']]
    
    plt.figure(figsize=(14, 8))
    df_pivot.plot(kind='bar', stacked=True, figsize=(14, 8), colormap='coolwarm_r')
    plt.title(f'{task} - 各模型评级分布', fontsize=16)
    plt.xlabel('模型', fontsize=12)
    plt.ylabel('评级数量', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.legend(title='评级')
    plt.tight_layout()
    
    rating_dist_chart_path = output_dir / 'chart_rating_distribution.png'
    plt.savefig(rating_dist_chart_path, dpi=300)
    print(f"📈 评级分布图已保存: {rating_dist_chart_path}")
    plt.close()


if __name__ == "__main__":
    task = 'TASK1'
    
    print("\n" + "="*80)
    print("评估结果统计与可视化分析")
    print("="*80 + "\n")
    
    output_dir = Path('evaluation_results') / task
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary = load_evaluation_summary(task)
    
    create_excel_report(task, summary, output_dir)
    
    create_visualizations(task, summary, output_dir)
    
    print(f"\n{'='*80}")
    print("✅ 分析完成！所有报告和图表已保存在目录中:")
    print(f"   {output_dir}")
    print(f"{'='*80}\n")
