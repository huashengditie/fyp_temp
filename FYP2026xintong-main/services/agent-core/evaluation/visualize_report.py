# -*- coding: utf-8 -*-
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import glob
import os

def run_comprehensive_analysis(file_path):
    target_order = [
        'dGPredictor', 'EnzRank', 'Database', 'MESearch',
        'MultiTool_Same', 'MultiTool_Mixed',
        'Neg_dG', 'Neg_Enz', 'Neg_DB', 'Neg_ME', 'Neg_Gen',
        'Greeting', 'Capability'
    ]

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    score_cols = ['judge_accuracy', 'judge_reasoning', 'judge_completeness', 'judge_total_score']
    for col in score_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['is_pass'] = df['judge_total_score'] > 7

    stats = df.groupby('category').agg({
        'judge_accuracy': ['mean', 'std'],
        'judge_reasoning': ['mean', 'std'],
        'judge_completeness': ['mean', 'std'],
        'judge_total_score': ['mean', 'std'],
        'is_pass': lambda x: x.mean() * 100,
        'id': 'count'
    })

    stats.columns = [
        'acc_mean', 'acc_std',
        'reas_mean', 'reas_std',
        'comp_mean', 'comp_std',
        'total_mean', 'total_std',
        'pass_rate', 'count'
    ]

    stats = stats.fillna(0)

    existing_order = [c for c in target_order if c in stats.index]
    stats = stats.reindex(existing_order)

    overall_acc, overall_acc_std = df['judge_accuracy'].mean(), df['judge_accuracy'].std()
    overall_reas, overall_reas_std = df['judge_reasoning'].mean(), df['judge_reasoning'].std()
    overall_comp, overall_comp_std = df['judge_completeness'].mean(), df['judge_completeness'].std()
    overall_total, overall_total_std = df['judge_total_score'].mean(), df['judge_total_score'].std()
    overall_pass = df['is_pass'].mean() * 100
    total_count = df['id'].count()

# print table
    line_width = 145
    print("\n" + "=" * line_width)
    print(f"{'AGENT PERFORMANCE EVALUATION REPORT (STABILITY ANALYSIS)':^145}")
    print("=" * line_width)
    header = (f"{'Task Category':<22} | {'Accuracy':<14} | {'Reasoning':<14} | "
              f"{'Completeness':<14} | {'Avg Total Score':<18} | {'Pass Rate':<10} | {'Count'}")
    print(header)
    print("-" * line_width)

    def fmt(m, s): return f"{m:>5.2f} ±{s:<5.2f}"

    for idx, row in stats.iterrows():
        print(f"{idx:<22} | "
              f"{fmt(row['acc_mean'], row['acc_std'])} | "
              f"{fmt(row['reas_mean'], row['reas_std'])} | "
              f"{fmt(row['comp_mean'], row['comp_std'])} | "
              f"{fmt(row['total_mean'], row['total_std'])} | "
              f"{row['pass_rate']:>8.1f}% | "
              f"{int(row['count']):<6}")

    print("-" * line_width)
    print(f"{'OVERALL (Total Sample)':<22} | "
          f"{fmt(overall_acc, overall_acc_std)} | "
          f"{fmt(overall_reas, overall_reas_std)} | "
          f"{fmt(overall_comp, overall_comp_std)} | "
          f"{fmt(overall_total, overall_total_std)} | "
          f"{overall_pass:>8.1f}% | "
          f"{int(total_count):<6}")
    print("=" * line_width)

    # visualize
    sns.set_theme(style="whitegrid")
    fig, ax1 = plt.subplots(figsize=(18, 9))

    x = np.arange(len(stats.index))
    width = 0.25

    ax1.bar(x - width, stats['acc_mean'], width, yerr=stats['acc_std'],
            label='Accuracy', color='#4C72B0', capsize=3, alpha=0.8)
    ax1.bar(x, stats['reas_mean'], width, yerr=stats['reas_std'],
            label='Reasoning', color='#55A868', capsize=3, alpha=0.8)
    ax1.bar(x + width, stats['comp_mean'], width, yerr=stats['comp_std'],
            label='Completeness', color='#C44E52', capsize=3, alpha=0.8)

    model_name = os.path.basename(file_path).replace('.csv', '').upper()
    ax1.set_title(f'Agent Performance Analysis: {model_name} (Mean ± SD)', fontsize=18, fontweight='bold', pad=25)
    ax1.set_ylabel('Scores (0-5 scale)', fontsize=13, fontweight='bold')
    ax1.set_ylim(0, 6.8)
    ax1.set_xticks(x)
    ax1.set_xticklabels(stats.index, rotation=30, ha='right', fontsize=11)
    ax1.legend(loc='upper left', frameon=True, shadow=True)

    ax2 = ax1.twinx()
    ax2.plot(x, stats['pass_rate'], color='#8172B3', marker='o', linewidth=3, markersize=8, label='Pass Rate (%)')
    ax2.set_ylabel('Pass Rate (%)', fontsize=13, color='#8172B3', fontweight='bold')
    ax2.set_ylim(0, 120)

    for i, val in enumerate(stats['pass_rate']):
        ax2.text(i, val + 5, f'{val:.0f}%', color='#8172B3', ha='center', fontweight='bold', fontsize=10)

    ax2.grid(False)
    ax2.legend(loc='upper right', frameon=True, shadow=True)

    plt.tight_layout()

    output_image = f'report_{model_name.lower()}.png'
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    print(f"\n[Done] Report saved to: {output_image}")
    plt.show()

if __name__ == "__main__":
    csv_files = glob.glob('*.csv')
    if csv_files:
        latest_report = max(csv_files, key=os.path.getmtime)
        run_comprehensive_analysis(latest_report)
    else:
        print("Error: No CSV report files found.")