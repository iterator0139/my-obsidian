#!/usr/bin/env python3
"""
将已有「个人任务中心」从 Dashboard/Chart 会员视图升级为免费方案。

环境变量：
  NOTION_TOKEN
  HUB_PAGE_ID       个人任务中心页面 ID（默认已创建的那个）

用法：
  export NOTION_TOKEN="ntn_..."
  export HUB_PAGE_ID="376825f4a72081efaf57c6f55037f692"
  python3 upgrade_free_overview.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

DEFAULT_HUB = "376825f4a72081efaf57c6f55037f692"
DEFAULT_DB = "4ada503c-ed82-46e3-8e5d-6e386f04f516"


def load_setup():
    path = Path(__file__).parent / "setup_notion_task_hub.py"
    spec = importlib.util.spec_from_file_location("setup", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    token = os.environ.get("NOTION_TOKEN", "").strip()
    hub_page_id = os.environ.get("HUB_PAGE_ID", DEFAULT_HUB).strip().replace("-", "")
    database_id = os.environ.get("DATABASE_ID", DEFAULT_DB).strip().replace("-", "")

    if not token:
        print("❌ 请设置 NOTION_TOKEN", file=sys.stderr)
        sys.exit(1)

    mod = load_setup()
    db = mod.notion_request("GET", f"/databases/{database_id}", token)
    data_source_id = db["data_sources"][0]["id"]
    prop_ids = mod.get_property_ids(token, data_source_id)

    print("🔧 升级免费总览方案…")

    def list_views() -> list[dict]:
        refs = mod.notion_request("GET", f"/views?database_id={database_id}", token)
        results = []
        for ref in refs.get("results", []):
            try:
                results.append(mod.notion_request("GET", f"/views/{ref['id']}", token))
            except RuntimeError:
                continue
        return results

    # 1. 删除 Dashboard / Chart 会员视图
    for view in list_views():
        if view.get("type") in ("dashboard", "chart"):
            print(f"   删除会员视图：{view.get('name')} ({view.get('type')})")
            mod.delete_view(token, view["id"])

    # 2. 若无「项目统计」则创建
    has_stats = any(v.get("name") == "📈 项目统计" for v in list_views())
    if not has_stats:
        print("   创建免费「📈 项目统计」视图…")
        mod.create_view(
            token,
            database_id=database_id,
            data_source_id=data_source_id,
            name="📈 项目统计",
            view_type="table",
            view_filter={"property": "状态", "status": {"equals": "已完成"}},
            configuration={
                "type": "table",
                "group_by": {
                    "type": "select",
                    "property_id": prop_ids["项目"],
                    "group_by": "option",
                    "sort": {"type": "manual"},
                },
            },
        )

    # 3. 主页插入总览区块 + 关联视图（若尚未存在）
    children = mod.notion_request("GET", f"/blocks/{hub_page_id}/children", token)
    has_overview = any(
        b.get("type") == "heading_2"
        and "快速总览" in (b.get("heading_2", {}).get("rich_text", [{}])[0].get("plain_text", ""))
        for b in children.get("results", [])
    )
    if not has_overview:
        print("   在主页末尾插入总览分区…")
        mod.append_hub_blocks(token, hub_page_id)
        print("   嵌入关联数据库视图…")
        mod.create_linked_overview(token, hub_page_id, data_source_id, prop_ids)
    else:
        print("   主页总览已存在，跳过")

    hub_url = f"https://www.notion.so/{hub_page_id.replace('-', '')}"
    print()
    print("✅ 升级完成！")
    print(f"   打开主页向下滚动查看「📊 快速总览」：{hub_url}")
    print("   数据库视图标签页里用 🗓️大盘 / 🎯Focus / 📅回溯 切换即可")


if __name__ == "__main__":
    main()
