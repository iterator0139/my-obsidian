#!/usr/bin/env python3
"""
将 Focus 从「所有进行中任务」改为「手动勾选今日重点」。

环境变量：NOTION_TOKEN
可选：DATABASE_ID, HUB_PAGE_ID
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

DEFAULT_DB = "4ada503c-ed82-46e3-8e5d-6e386f04f516"
DEFAULT_HUB = "376825f4a72081efaf57c6f55037f692"


def load_setup():
    path = Path(__file__).parent / "setup_notion_task_hub.py"
    spec = importlib.util.spec_from_file_location("setup", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    token = os.environ.get("NOTION_TOKEN", "").strip()
    database_id = os.environ.get("DATABASE_ID", DEFAULT_DB).strip().replace("-", "")
    hub_page_id = os.environ.get("HUB_PAGE_ID", DEFAULT_HUB).strip().replace("-", "")

    if not token:
        print("❌ 请设置 NOTION_TOKEN", file=sys.stderr)
        sys.exit(1)

    mod = load_setup()
    db = mod.notion_request("GET", f"/databases/{database_id}", token)
    data_source_id = db["data_sources"][0]["id"]

    print("🎯 升级 Focus 为手动挑选模式…")
    print("   添加「今日重点」勾选字段…")
    mod.ensure_focus_property(token, data_source_id)
    prop_ids = mod.get_property_ids(token, data_source_id)

    print("   更新 Focus 视图…")
    mod.upsert_focus_views(token, database_id, data_source_id, hub_page_id, prop_ids)

    hub_url = f"https://www.notion.so/{hub_page_id.replace('-', '')}"
    print()
    print("✅ Focus 升级完成！")
    print(f"   主页：{hub_url}")
    print()
    print("📌 每天早上：")
    print("   1. 打开「📋 全部任务」，取消昨天勾选的 ☑️今日重点")
    print("   2. 今天最多勾选 3 个任务的 ☑️今日重点")
    print("   3. 打开「🎯 Focus 今日重点」—— 只显示你亲手选的任务")


if __name__ == "__main__":
    main()
