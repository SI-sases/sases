# -*- coding: utf-8 -*-
"""新建任务上下文：docs/tasks/active/CURRENT_TASK.md。

用法：
  python scripts/new_task.py --task p3-build
"""
import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
ACTIVE = ROOT / 'docs' / 'tasks' / 'active'
TEMPLATE = ROOT / 'docs' / 'tasks' / 'CURRENT_TASK.template.md'
TARGET = ACTIVE / 'CURRENT_TASK.md'

TEMPLATE_TEXT = """## 当前任务：{task}

目标：<一句话>
涉及文件：<文件列表>
涉及表：<表列表>
验收标准：<肉眼可验证的现象>
不做什么：<明确排除>
回滚：git checkout <pre-{task}>

## 坑点

- <逐条列>

## 归档纪律

- 任务结束时只输出 [SUMMARY]，禁止自动归档
- 用户明确说"执行归档"时，才调：
  `python scripts/archive_task.py --task {task}`
- 归档前必须先跑 `--dry-run` 展示将移动的文件
- 归档后 task_context 残留和 task__ 分片残留必须都为 0

版本：{today} / 适用任务：{task}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--task', required=True)
    ap.add_argument('--force', action='store_true', help='覆盖已存在的 CURRENT_TASK.md')
    args = ap.parse_args()

    if TARGET.exists() and not args.force:
        print('[FATAL] 已有活跃任务: {}'.format(TARGET))
        print('       先归档旧任务：python scripts/archive_task.py --task <旧任务名>')
        print('       或强制覆盖：python scripts/new_task.py --task {} --force'.format(args.task))
        sys.exit(1)

    ACTIVE.mkdir(parents=True, exist_ok=True)
    content = TEMPLATE_TEXT.format(task=args.task, today=date.today().isoformat())
    TARGET.write_text(content, encoding='utf-8')
    print('[new_task] 已生成: {}'.format(TARGET))
    print('[new_task] 请编辑填入内容，然后跑：')
    print('          python scripts/import_project_docs.py --sync')


if __name__ == '__main__':
    main()
