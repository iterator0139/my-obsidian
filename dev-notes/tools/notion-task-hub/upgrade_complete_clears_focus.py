#!/usr/bin/env python3
"""
升级 Focus / 四象限：任务标为「已完成」后自动从面板消失。

原理：视图筛选改为「今日重点 = 勾选 且 状态 ≠ 已完成」。
在任意视图把状态改为「已完成」后，任务会立刻从 Focus 与四象限移除。

环境变量：
  NOTION_TOKEN   Personal Access Token
  DATABASE_ID    任务总表 database ID（可选，默认见脚本内 DEFAULT_DB）

用法：
  export NOTION_TOKEN="ntn_..."
  export DATABASE_ID="你的32位database_id"
  python3 upgrade_complete_clears_focus.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

DEFAULT_DB = "4ada503c-ed82-46e3-8e5d-6e386f04f516"


def load_setup():
    path = Path(__file__).parent / "setup_notion_task_hub.py"
    spec = importlib.util.spec_from_file_location("setup", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    token = os.environ.get("NOTION_TOKEN", "").strip()
    database_id = os.environ.get("DATABASE_ID", DEFAULT_DB).strip().replace("-", "")

    if not token:
        print("❌ 请设置 NOTION_TOKEN", file=sys.stderr)
        sys.exit(1)

    mod = load_setup()
    db = mod.notion_request("GET", f"/databases/{database_id}", token)
    data_source_id = db["data_sources"][0]["id"]

    print("✅ 升级 Focus / 四象限筛选：完成后自动移出面板…")
    updated = mod.upgrade_focus_quadrant_filters(token, database_id, data_source_id)

    if updated:
        for name in updated:
            print(f"   已更新「{name}」")
    else:
        print("   所有相关视图已是最新筛选，无需变更")

    print()
    print("✅ 完成！")
    print("   在任意视图把任务状态改为「已完成」，会立刻从 Focus / 四象限消失。")
    print()
    print("📌 可选（Notion 内自动化，自动取消 ☑️今日重点）：")
    print("   1. 打开「任务总表」→ 右上角 ⚡ → New automation")
    print("   2. 触发：Property edited → 状态 → 已完成")
    print("   3. 动作：Edit property → 今日重点 → Unchecked")
    print("   4. （可选）再添加动作：Edit property → 象限 → Empty")


if __name__ == "__main__":
    main()
