import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description='汇总 hard_cases.csv，输出按类漏检样例清单')
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--output-md', type=Path, default=Path('docs/补采集优先级_检测模型.md'))
    parser.add_argument('--top-k', type=int, default=20)
    args = parser.parse_args()

    rows = []
    with args.csv.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        raise SystemExit('CSV 为空，无法生成清单。')

    class_names = [c.replace('fn_', '') for c in rows[0].keys() if c.startswith('fn_') and c != 'fn_total']

    lines = [
        '# 补采集优先级清单（检测模型）',
        '',
        f'- 样例来源：{args.csv}',
        f'- TopK：{args.top_k}',
        '',
    ]

    for cls in class_names:
        key = f'fn_{cls}'
        rows_sorted = sorted(rows, key=lambda r: int(float(r.get(key, 0))), reverse=True)
        lines += [
            f'## {cls}',
            '',
        ]
        count = 0
        for r in rows_sorted:
            v = int(float(r.get(key, 0)))
            if v <= 0:
                break
            lines.append(f"- {r['image']} (FN_{cls}={v})")
            count += 1
            if count >= args.top_k:
                break
        if count == 0:
            lines.append('- 无有效样例')
        lines.append('')

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text('\n'.join(lines), encoding='utf-8')
    print(f'清单已生成：{args.output_md}')


if __name__ == '__main__':
    main()
