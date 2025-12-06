import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from pathlib import Path

# ==============================================================================
# --- 1. 全局样式和参数配置 ---
# ==============================================================================

# ⭐⭐⭐ 终极字体解决方案 ⭐⭐⭐
# 将您在第一步中复制的字体路径，粘贴到下面的引号中
# 如果下面的路径无效或您找到了其他中文字体，请替换它
FONT_PATH = '/System/Library/Fonts/PingFang.ttc'  # 这是一个Mac上常见的黑体路径

# 检查字体路径是否存在，如果不存在则提示
font_path_obj = Path(FONT_PATH)
if not font_path_obj.exists():
    print(f"❌ 警告：指定的字体路径不存在: {FONT_PATH}")
    print("请按照说明，在您的Mac上找到一个有效的中文字体路径并替换它！")
    # 如果找不到字体，就使用默认字体，这会导致方框问题，但程序不会崩溃
    font_prop = fm.FontProperties()
else:
    # 从指定路径加载字体
    font_prop = fm.FontProperties(fname=FONT_PATH)

# 其他配置保持不变
FONT_CONFIG = {
    'title': 30, 'label': 25, 'tick': 18, 'annotation': 18,
    'legend_title': 25, 'legend_text': 20, 'table_header': 20, 'table_cell': 16,
}

# --- Nature风格配色方案 ---
NATURE_COLORS = {
    'A': '#3B7A9E', 'B': '#99C7D6', 'C': '#F2B872', 'D': '#D87A6B'
}
AVERAGE_SCORE_PALETTE = sns.color_palette(f"blend:{NATURE_COLORS['A']},{NATURE_COLORS['B']}", n_colors=9)

# --- Matplotlib 全局设置 (解决中文乱码) ---
# ⭐⭐⭐ 这里是关键修改！我们将字体换回 'Heiti TC' ⭐⭐⭐
plt.rcParams['font.sans-serif'] = ['Heiti TC'] 
plt.rcParams['axes.unicode_minus'] = False
plt.style.use('seaborn-v0_8-whitegrid')

# ==============================================================================
# --- 2. 最终数据 (保持不变) ---
# ==============================================================================
final_data = {
    'gpt-5': {'average_score': 3.78, 'dist': {'A': 41, 'B': 7, 'C': 2, 'D': 0}},
    'doubao-pro-256k': {'average_score': 3.60, 'dist': {'A': 41, 'B': 2, 'C': 3, 'D': 4}},
    'kimi-k2-thinking': {'average_score': 3.60, 'dist': {'A': 41, 'B': 1, 'C': 5, 'D': 3}},
    'gemini-2.5-flash': {'average_score': 3.36, 'dist': {'A': 35, 'B': 5, 'C': 3, 'D': 7}},
    'grok-3': {'average_score': 3.26, 'dist': {'A': 35, 'B': 2, 'C': 4, 'D': 9}},
    'qwen-plus': {'average_score': 3.16, 'dist': {'A': 33, 'B': 2, 'C': 5, 'D': 10}},
    'glm-4.6': {'average_score': 3.08, 'dist': {'A': 25, 'B': 10, 'C': 9, 'D': 6}},
    'deepseek-chat': {'average_score': 3.00, 'dist': {'A': 28, 'B': 6, 'C': 4, 'D': 12}},
    'gpt-40': {'average_score': 2.54, 'dist': {'A': 11, 'B': 15, 'C': 14, 'D': 10}}
}

# ==============================================================================
# --- 3. 数据处理 (保持不变) ---
# ==============================================================================
df_scores = pd.DataFrame.from_dict(final_data, orient='index').sort_values('average_score', ascending=False)
df_scores.index.name = '模型'
ratings_data = []
for model, data in final_data.items():
    for rating, count in data['dist'].items():
        ratings_data.append({'模型': model, '评级': rating, '数量': count})
df_ratings = pd.DataFrame(ratings_data)

# ==============================================================================
# --- 4. 可视化函数 (保持不变) ---
# ==============================================================================
def create_summary_table_image(output_dir):
    """将最终结果表格渲染成高质量PNG图片"""
    table_df = df_scores.copy()
    table_df['A'] = [final_data[model]['dist']['A'] for model in table_df.index]
    table_df['B'] = [final_data[model]['dist']['B'] for model in table_df.index]
    table_df['C'] = [final_data[model]['dist']['C'] for model in table_df.index]
    table_df['D'] = [final_data[model]['dist']['D'] for model in table_df.index]
    table_df['排名'] = range(1, len(table_df) + 1)
    table_df = table_df.reset_index()
    table_df = table_df[['排名', '模型', 'average_score', 'A', 'B', 'C', 'D']]
    table_df = table_df.rename(columns={'average_score': '平均分'})
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis('tight'); ax.axis('off')
    the_table = ax.table(cellText=table_df.values, colLabels=table_df.columns, loc='center', cellLoc='center', colColours=['#f2f2f2']*len(table_df.columns))
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(FONT_CONFIG['table_cell'])
    the_table.scale(1.2, 2.5)
    for (i, j), cell in the_table.get_celld().items():
        if i == 0: cell.set_text_props(weight='bold', color='black', size=FONT_CONFIG['table_header']); cell.set_facecolor('#e6e6e6')
        if j == 1: cell.set_text_props(ha='left')
        cell.set_edgecolor('w')
    plt.title('评估结果汇总', fontsize=FONT_CONFIG['title'], pad=20)
    table_path = output_dir / 'final_table_summary.png'
    plt.savefig(table_path, dpi=300, bbox_inches='tight', pad_inches=0.5)
    print(f"📊 汇总表格图已保存: {table_path}")
    plt.close()

def create_enhanced_visualizations(output_dir):
    """生成并保存优化后的可视化图表"""
    # 图一：模型平均分对比柱状图
    plt.figure(figsize=(16, 10))
    ax1 = sns.barplot(x=df_scores.index, y='average_score', data=df_scores, palette=AVERAGE_SCORE_PALETTE)
    plt.title('各模型综合表现对比 (平均分)', fontsize=FONT_CONFIG['title'], pad=20)
    plt.xlabel('模型', fontsize=FONT_CONFIG['label'], labelpad=15); plt.ylabel('平均分 (A=4, B=3, C=2, D=1)', fontsize=FONT_CONFIG['label'])
    plt.xticks(rotation=45, ha='right', fontsize=FONT_CONFIG['tick']); plt.yticks(fontsize=FONT_CONFIG['tick'])
    plt.ylim(0, 4.3)
    for p in ax1.patches: ax1.annotate(f'{p.get_height():.2f}', (p.get_x() + p.get_width() / 2., p.get_height()), ha='center', va='center', fontsize=FONT_CONFIG['annotation'], color='black', xytext=(0, 15), textcoords='offset points', fontweight='bold')
    ax1.grid(axis='y', linestyle='--', alpha=0.6); sns.despine(); plt.tight_layout()
    avg_score_chart_path = output_dir / 'final_chart_average_scores.png'
    plt.savefig(avg_score_chart_path, dpi=300)
    print(f"📈 [Nature风格] 平均分对比图已保存: {avg_score_chart_path}")
    plt.close()
    # 图二：评级分布堆叠柱状图
    df_pivot = df_ratings.pivot(index='模型', columns='评级', values='数量').loc[df_scores.index]
    plt.figure(figsize=(16, 10))
    ax2 = df_pivot[['A', 'B', 'C', 'D']].plot(kind='bar', stacked=True, figsize=(16, 10), color=[NATURE_COLORS['A'], NATURE_COLORS['B'], NATURE_COLORS['C'], NATURE_COLORS['D']], edgecolor='white', linewidth=0.5)
    for c in ax2.containers:
        labels = [int(v) if v > 5 else '' for v in c.datavalues]
        ax2.bar_label(c, labels=labels, label_type='center', fontsize=FONT_CONFIG['annotation']-2, color='white', fontweight='bold')
    plt.title('各模型回答评级分布', fontsize=FONT_CONFIG['title'], pad=20)
    plt.xlabel('模型', fontsize=FONT_CONFIG['label'], labelpad=15); plt.ylabel('评级数量', fontsize=FONT_CONFIG['label'])
    plt.xticks(rotation=45, ha='right', fontsize=FONT_CONFIG['tick']); plt.yticks(fontsize=FONT_CONFIG['tick'])
    legend = plt.legend(title='评级', bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=FONT_CONFIG['legend_text'], title_fontsize=FONT_CONFIG['legend_title'])
    legend.get_frame().set_edgecolor('w')
    ax2.grid(axis='y', linestyle='--', alpha=0.6); sns.despine(); plt.tight_layout(rect=[0, 0, 0.9, 1])
    rating_dist_chart_path = output_dir / 'final_chart_rating_distribution.png'
    plt.savefig(rating_dist_chart_path, dpi=300)
    print(f"📈 [Nature风格] 评级分布图已保存: {rating_dist_chart_path}")
    plt.close()

# ==============================================================================
# --- 5. 主程序入口 (保持不变) ---
# ==============================================================================
if __name__ == "__main__":
    task = 'TASK1'
    print("\n" + "="*80 + "\n最终评估结果可视化 (Nature风格版)\n" + "="*80 + "\n")
    output_dir = Path('evaluation_results') / task
    output_dir.mkdir(parents=True, exist_ok=True)
    create_summary_table_image(output_dir)
    create_enhanced_visualizations(output_dir)
    print(f"\n{'='*80}\n✅ 可视化完成！所有图表和表格已保存在目录中:\n   {output_dir}\n{'='*80}\n")