#!/usr/bin/env python3
"""为任务总表添加「象限」字段和四象限看板视图。"""

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


def has_quadrant_view(mod, token: str, database_id: str) -> bool:
    refs = mod.notion_request("GET", f"/views?database_id={database_id}", token)
    for ref in refs.get("results", []):
        try:
            view = mod.notion_request("GET", f"/views/{ref['id']}", token)
        except RuntimeError:
            continue
        if view.get("name") == "🔲 四象限矩阵":
            return True
    return False


def main() -> None:
    token = os.environ.get("NOTION_TOKEN", "").strip()
    database_id = os.environ.get("DATABASE_ID", DEFAULT_DB).strip().replace("-", "")

    if not token:
        print("❌ 请设置 NOTION_TOKEN", file=sys.stderr)
        sys.exit(1)

    mod = load_setup()
    db = mod.notion_request("GET", f"/databases/{database_id}", token)
    data_source_id = db["data_sources"][0]["id"]

    print("🔲 添加四象限矩阵…")
    mod.ensure_quadrant_property(token, data_source_id)
    prop_ids = mod.get_property_ids(token, data_source_id)

    if not has_quadrant_view(mod, token, database_id):
        mod.create_view(
            token,
            database_id=database_id,
            data_source_id=data_source_id,
            name="🔲 四象限矩阵",
            view_type="board",
            view_filter=mod.focus_view_filter(),
            configuration=mod.quadrant_board_configuration(prop_ids),
        )
        print("   已创建「🔲 四象限矩阵」视图")
    else:
        print("   视图已存在，跳过创建")

    # 刷新 Focus 列表，显示象限列
    refs = mod.notion_request("GET", f"/views?database_id={database_id}", token)
    for ref in refs.get("results", []):
        view = mod.notion_request("GET", f"/views/{ref['id']}", token)
        if view.get("name") == "🎯 Focus 今日重点" and view.get("type") == "list":
            mod.update_view(
                token,
                view["id"],
                {"configuration": mod.focus_list_configuration(prop_ids)},
            )
            print("   已更新 Focus 列表显示象限列")

    print()
    print("✅ 完成！使用方式：")
    print("   1. 在「全部任务」勾选 ☑️今日重点")
    print("   2. 打开「🔲 四象限矩阵」，把任务拖进对应象限列")
    print("   3. 优先做 ①重要且紧急 → ②重要不紧急")


if __name__ == "__main__":
    main()
