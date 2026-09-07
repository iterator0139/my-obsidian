#!/usr/bin/env python3
"""
一键在 Notion 创建「个人任务中心」—— 一表流任务管理系统。

依赖：Python 3.9+，无需第三方包。

环境变量：
  NOTION_TOKEN      Personal Access Token（推荐）或其他 Bearer token
  PARENT_PAGE_ID    挂载父页面 ID（PAT 创建者能访问即可，无需 Add connections）

用法（PAT，推荐）：
  export NOTION_TOKEN="ntn_你的PAT"
  export PARENT_PAGE_ID="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  python3 setup_notion_task_hub.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

NOTION_VERSION = "2026-03-11"
BASE_URL = "https://api.notion.com/v1"

# ── 字段定义 ──────────────────────────────────────────────

PROJECT_OPTIONS = [
    {"name": "个人成长", "color": "purple"},
    {"name": "工作", "color": "blue"},
    {"name": "生活琐事", "color": "green"},
]

STATUS_OPTIONS = [
    {"name": "未开始", "color": "gray"},
    {"name": "进行中", "color": "blue"},
    {"name": "已完成", "color": "green"},
]

QUADRANT_OPTIONS = [
    {"name": "① 重要且紧急", "color": "red"},
    {"name": "② 重要不紧急", "color": "blue"},
    {"name": "③ 紧急不重要", "color": "orange"},
    {"name": "④ 不重要不紧急", "color": "gray"},
]

AI_WEEKLY_PROMPT = (
    "请分析我本周已完成的任务，总结我在各个项目上的时间投入比例，"
    "并指出有哪些任务经常延期，给出下周优化建议。"
)


# ── HTTP 封装 ─────────────────────────────────────────────

def notion_request(
    method: str,
    path: str,
    token: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        raise RuntimeError(f"Notion API {method} {path} → {e.code}: {detail}") from e


# ── 创建流程 ─────────────────────────────────────────────

def create_hub_page(token: str, parent_page_id: str) -> str:
    resp = notion_request(
        "POST",
        "/pages",
        token,
        {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "icon": {"type": "emoji", "emoji": "🎯"},
            "properties": {
                "title": {
                    "title": [{"type": "text", "text": {"content": "个人任务中心"}}],
                },
            },
            "children": [
                {
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": (
                                        "一表流任务管理：所有任务写在「任务总表」里，"
                                        "通过不同视图切换大盘 / Focus / 回溯。"
                                        "每天早上在「全部任务」勾选 ☑️今日重点（建议 3 个），"
                                        "Focus 视图只显示你亲手挑选的任务；"
                                        "任务标为「已完成」后会自动从 Focus / 四象限消失；"
                                        "每周日在下方 AI 指令处生成周报。"
                                    ),
                                },
                            },
                        ],
                        "icon": {"type": "emoji", "emoji": "💡"},
                        "color": "blue_background",
                    },
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "📊 周日 AI 周报指令"}},
                        ],
                    },
                },
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [
                            {"type": "text", "text": {"content": AI_WEEKLY_PROMPT}},
                        ],
                        "language": "plain text",
                    },
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": (
                                        "使用方法：打开「任务总表」→ 点击右上角 Notion AI → "
                                        "粘贴上方指令 → 选择「当前数据库」作为上下文。"
                                    ),
                                },
                            },
                        ],
                    },
                },
            ],
        },
    )
    return resp["id"]


def create_database(token: str, hub_page_id: str) -> dict[str, Any]:
    return notion_request(
        "POST",
        "/databases",
        token,
        {
            "parent": {"type": "page_id", "page_id": hub_page_id},
            "title": [{"type": "text", "text": {"content": "任务总表"}}],
            "icon": {"type": "emoji", "emoji": "📋"},
            "is_inline": False,
            "initial_data_source": {
                "properties": {
                    "任务名称": {"title": {}},
                    "项目": {
                        "select": {"options": PROJECT_OPTIONS},
                    },
                    "状态": {
                        "status": {"options": STATUS_OPTIONS},
                    },
                    "日期": {"date": {}},
                    "复盘笔记": {"rich_text": {}},
                    "今日重点": {"checkbox": {}},
                    "象限": {"select": {"options": QUADRANT_OPTIONS}},
                },
            },
        },
    )


def ensure_quadrant_property(token: str, data_source_id: str) -> None:
    notion_request(
        "PATCH",
        f"/data_sources/{data_source_id}",
        token,
        {"properties": {"象限": {"select": {"options": QUADRANT_OPTIONS}}}},
    )


def ensure_focus_property(token: str, data_source_id: str) -> None:
    """为已有数据库补充「今日重点」勾选字段。"""
    notion_request(
        "PATCH",
        f"/data_sources/{data_source_id}",
        token,
        {"properties": {"今日重点": {"checkbox": {}}}},
    )


def legacy_focus_view_filter() -> dict[str, Any]:
    """旧版 Focus / 四象限筛选（仅今日重点，不含完成态排除）。"""
    return {"property": "今日重点", "checkbox": {"equals": True}}


def focus_view_filter() -> dict[str, Any]:
    """Focus / 四象限：今日重点且未完成（标记完成后自动从面板消失）。"""
    return {
        "and": [
            {"property": "今日重点", "checkbox": {"equals": True}},
            {"property": "状态", "status": {"does_not_equal": "已完成"}},
        ],
    }


def is_focus_panel_filter(view_filter: dict[str, Any] | None) -> bool:
    if not view_filter:
        return False
    return view_filter in {focus_view_filter(), legacy_focus_view_filter()}


def focus_list_configuration(prop_ids: dict[str, str]) -> dict[str, Any]:
    props = [
        {"property_id": "title", "visible": True},
        {"property_id": prop_ids["项目"], "visible": True},
        {"property_id": prop_ids["状态"], "visible": True},
        {"property_id": prop_ids["日期"], "visible": True},
        {"property_id": prop_ids["今日重点"], "visible": True},
    ]
    if "象限" in prop_ids:
        props.insert(3, {"property_id": prop_ids["象限"], "visible": True})
    return {"type": "list", "properties": props}


def quadrant_board_configuration(prop_ids: dict[str, str]) -> dict[str, Any]:
    return {
        "type": "board",
        "group_by": {
            "type": "select",
            "property_id": prop_ids["象限"],
            "group_by": "option",
            "sort": {"type": "manual"},
        },
        "card_layout": "compact",
    }


def get_property_ids(token: str, data_source_id: str) -> dict[str, str]:
    ds = notion_request("GET", f"/data_sources/{data_source_id}", token)
    return {name: prop["id"] for name, prop in ds["properties"].items()}


def rename_default_view(token: str, database_id: str) -> None:
    views = notion_request(
        "GET", f"/views?database_id={database_id}", token
    )
    if not views.get("results"):
        return
    default_id = views["results"][0]["id"]
    notion_request(
        "PATCH",
        f"/views/{default_id}",
        token,
        {"name": "📋 全部任务"},
    )


def create_view(
    token: str,
    *,
    database_id: str | None = None,
    data_source_id: str,
    name: str,
    view_type: str,
    view_filter: dict[str, Any] | None = None,
    sorts: list[dict[str, Any]] | None = None,
    configuration: dict[str, Any] | None = None,
    position: dict[str, Any] | None = None,
    view_id: str | None = None,
    placement: dict[str, Any] | None = None,
    create_database: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "data_source_id": data_source_id,
        "name": name,
        "type": view_type,
    }
    if view_id:
        body["view_id"] = view_id
    elif create_database:
        body["create_database"] = create_database
    elif database_id:
        body["database_id"] = database_id
    else:
        raise ValueError("create_view requires database_id, view_id, or create_database")
    if view_filter:
        body["filter"] = view_filter
    if sorts:
        body["sorts"] = sorts
    if configuration:
        body["configuration"] = configuration
    if position:
        body["position"] = position
    if placement:
        body["placement"] = placement
    return notion_request("POST", "/views", token, body)


def append_hub_blocks(token: str, hub_page_id: str) -> None:
    """在主页末尾追加总览分区标题（关联视图由 create_linked_overview 追加）。"""
    notion_request(
        "PATCH",
        f"/blocks/{hub_page_id}/children",
        token,
        {
            "children": [
                {
                    "object": "block",
                    "type": "divider",
                    "divider": {},
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "📊 快速总览（免费版）"},
                            },
                        ],
                    },
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": (
                                        "下方三个关联视图与任务总表数据同步，"
                                        "无需 Dashboard 会员。"
                                    ),
                                },
                            },
                        ],
                    },
                },
            ],
        },
    )


def create_linked_overview(
    token: str,
    hub_page_id: str,
    data_source_id: str,
    prop_ids: dict[str, str],
) -> dict[str, str]:
    """在主页嵌入关联数据库视图（Timeline / Board / Calendar），免费可用。"""
    pid = prop_ids
    parent = {"type": "page_id", "page_id": hub_page_id}
    urls: dict[str, str] = {}

    specs = [
        (
            "linked_timeline",
            "🗓️ 大盘",
            "timeline",
            None,
            {
                "type": "timeline",
                "date_property_id": pid["日期"],
                "show_table": False,
                "color_by": True,
                "preference": {"zoom_level": "month"},
            },
        ),
        (
            "linked_focus",
            "🎯 Focus",
            "list",
            focus_view_filter(),
            focus_list_configuration(pid),
        ),
        (
            "linked_history",
            "📅 回溯",
            "calendar",
            {"property": "状态", "status": {"equals": "已完成"}},
            {
                "type": "calendar",
                "date_property_id": pid["日期"],
                "view_range": "month",
            },
        ),
    ]

    for key, name, view_type, view_filter, configuration in specs:
        view = create_view(
            token,
            data_source_id=data_source_id,
            name=name,
            view_type=view_type,
            view_filter=view_filter,
            configuration=configuration,
            create_database={"parent": parent},
        )
        urls[key] = view.get("url", "")
        time.sleep(0.3)

    return urls


def delete_view(token: str, view_id: str) -> None:
    notion_request("DELETE", f"/views/{view_id}", token)


def update_view(token: str, view_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return notion_request("PATCH", f"/views/{view_id}", token, body)


def _is_focus_view_name(name: str) -> bool:
    return name in {"🎯 Focus 当前面板", "🎯 Focus", "🎯 Focus 今日重点"} or name.startswith("🎯 Focus")


def _create_focus_list_view(
    token: str,
    *,
    database_id: str,
    data_source_id: str,
    prop_ids: dict[str, str],
    name: str,
    position: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return create_view(
        token,
        database_id=database_id,
        data_source_id=data_source_id,
        name=name,
        view_type="list",
        view_filter=focus_view_filter(),
        sorts=[{"property": "日期", "direction": "ascending"}],
        configuration=focus_list_configuration(prop_ids),
        position=position,
    )


def _is_quadrant_view_name(name: str) -> bool:
    return name in {"🔲 四象限矩阵", "🔲 四象限"} or name.startswith("🔲 四象限")


def upgrade_focus_quadrant_filters(
    token: str,
    database_id: str,
    data_source_id: str,
) -> list[str]:
    """将 Focus / 四象限视图筛选升级为「今日重点且未完成」。"""
    updated: list[str] = []
    target_filter = focus_view_filter()
    seen: set[str] = set()

    for param in (f"database_id={database_id}", f"data_source_id={data_source_id}"):
        refs = notion_request("GET", f"/views?{param}", token)
        for ref in refs.get("results", []):
            vid = ref["id"]
            if vid in seen:
                continue
            seen.add(vid)

            try:
                view = notion_request("GET", f"/views/{vid}", token)
            except RuntimeError:
                continue

            name = view.get("name", "")
            view_type = view.get("type", "")
            current_filter = view.get("filter")

            is_focus_list = _is_focus_view_name(name) and view_type == "list"
            is_quadrant_board = _is_quadrant_view_name(name) and view_type == "board"
            if not (is_focus_list or is_quadrant_board):
                continue
            if current_filter == target_filter:
                continue

            update_view(token, vid, {"filter": target_filter})
            updated.append(name)

    return updated


def upsert_focus_views(
    token: str,
    database_id: str,
    data_source_id: str,
    hub_page_id: str,
    prop_ids: dict[str, str],
) -> None:
    """将 Focus 统一为「今日重点」列表。关联库先建新视图再删旧视图。"""
    seen: set[str] = set()
    main_ok = False
    linked_parent_dbs: set[str] = set()

    for param in (f"database_id={database_id}", f"data_source_id={data_source_id}"):
        refs = notion_request("GET", f"/views?{param}", token)
        for ref in refs.get("results", []):
            vid = ref["id"]
            if vid in seen:
                continue
            seen.add(vid)
            try:
                view = notion_request("GET", f"/views/{vid}", token)
            except RuntimeError:
                continue

            name = view.get("name", "")
            if not _is_focus_view_name(name):
                continue

            parent_db = view.get("parent", {}).get("database_id", "")
            is_main = parent_db.replace("-", "") == database_id.replace("-", "")
            target_name = "🎯 Focus 今日重点" if is_main else "🎯 Focus"

            if view.get("type") == "list" and is_focus_panel_filter(view.get("filter")):
                if is_main:
                    main_ok = True
                else:
                    linked_parent_dbs.add(parent_db.replace("-", ""))
                continue

            # 先在同库新建 list 视图，再删旧视图（避免「最后一个视图不可删」）
            _create_focus_list_view(
                token,
                database_id=parent_db,
                data_source_id=data_source_id,
                prop_ids=prop_ids,
                name=target_name,
                position={"type": "start"} if is_main else None,
            )
            try:
                delete_view(token, vid)
            except RuntimeError:
                pass

            if is_main:
                main_ok = True
            else:
                linked_parent_dbs.add(parent_db.replace("-", ""))

    if not main_ok:
        _create_focus_list_view(
            token,
            database_id=database_id,
            data_source_id=data_source_id,
            prop_ids=prop_ids,
            name="🎯 Focus 今日重点",
            position={"type": "start"},
        )

    if not linked_parent_dbs:
        create_view(
            token,
            data_source_id=data_source_id,
            name="🎯 Focus",
            view_type="list",
            view_filter=focus_view_filter(),
            sorts=[{"property": "日期", "direction": "ascending"}],
            configuration=focus_list_configuration(prop_ids),
            create_database={"parent": {"type": "page_id", "page_id": hub_page_id}},
        )


def create_all_views(
    token: str,
    database_id: str,
    data_source_id: str,
    prop_ids: dict[str, str],
) -> dict[str, str]:
    pid = prop_ids

    # 1. 大盘视图 — Timeline（按项目着色）
    timeline = create_view(
        token,
        database_id=database_id,
        data_source_id=data_source_id,
        name="🗓️ 大盘视图",
        view_type="timeline",
        position={"type": "start"},
        configuration={
            "type": "timeline",
            "date_property_id": pid["日期"],
            "show_table": True,
            "color_by": True,
            "preference": {"zoom_level": "month"},
        },
    )

    # 2. Focus — 仅显示手动勾选「今日重点」的任务（建议每天 3 个）
    focus = create_view(
        token,
        database_id=database_id,
        data_source_id=data_source_id,
        name="🎯 Focus 今日重点",
        view_type="list",
        view_filter=focus_view_filter(),
        configuration=focus_list_configuration(pid),
        sorts=[{"property": "日期", "direction": "ascending"}],
    )

    # 3. 四象限 — 当天今日重点按重要/紧急分类
    quadrant = create_view(
        token,
        database_id=database_id,
        data_source_id=data_source_id,
        name="🔲 四象限矩阵",
        view_type="board",
        view_filter=focus_view_filter(),
        configuration=quadrant_board_configuration(pid),
    )

    # 4. 回溯视图 — 日历，仅「已完成」
    history = create_view(
        token,
        database_id=database_id,
        data_source_id=data_source_id,
        name="📅 回溯视图",
        view_type="calendar",
        view_filter={
            "property": "状态",
            "status": {"equals": "已完成"},
        },
        configuration={
            "type": "calendar",
            "date_property_id": pid["日期"],
            "view_range": "month",
            "show_weekends": True,
        },
    )

    # 5. 项目统计 — 表格分组（免费，替代 Chart 会员视图）
    stats = create_view(
        token,
        database_id=database_id,
        data_source_id=data_source_id,
        name="📈 项目统计",
        view_type="table",
        view_filter={
            "property": "状态",
            "status": {"equals": "已完成"},
        },
        configuration={
            "type": "table",
            "group_by": {
                "type": "select",
                "property_id": pid["项目"],
                "group_by": "option",
                "sort": {"type": "manual"},
            },
        },
    )

    return {
        "timeline": timeline.get("url", ""),
        "focus": focus.get("url", ""),
        "quadrant": quadrant.get("url", ""),
        "history": history.get("url", ""),
        "stats": stats.get("url", ""),
    }


def seed_sample_tasks(
    token: str,
    data_source_id: str,
) -> None:
    """写入 3 条示例任务，方便立刻体验各视图。"""
    samples = [
        {
            "任务名称": "阅读《深度工作》30 分钟",
            "项目": "个人成长",
            "状态": "进行中",
            "日期": {"start": "2026-06-05", "end": "2026-06-10"},
            "复盘笔记": "",
        },
        {
            "任务名称": "完成 Q2 项目复盘文档",
            "项目": "工作",
            "状态": "未开始",
            "日期": {"start": "2026-06-08", "end": "2026-06-12"},
            "复盘笔记": "",
        },
        {
            "任务名称": "预约体检",
            "项目": "生活琐事",
            "状态": "已完成",
            "日期": {"start": "2026-06-03", "end": "2026-06-03"},
            "复盘笔记": "已预约 6/15 上午",
        },
    ]
    for task in samples:
        notion_request(
            "POST",
            "/pages",
            token,
            {
                "parent": {"type": "data_source_id", "data_source_id": data_source_id},
                "properties": {
                    "任务名称": {
                        "title": [
                            {"type": "text", "text": {"content": task["任务名称"]}},
                        ],
                    },
                    "项目": {"select": {"name": task["项目"]}},
                    "状态": {"status": {"name": task["状态"]}},
                    "日期": {"date": task["日期"]},
                    "复盘笔记": {
                        "rich_text": [
                            {"type": "text", "text": {"content": task["复盘笔记"]}},
                        ],
                    },
                },
            },
        )
        time.sleep(0.3)  # 避免 rate limit


def main() -> None:
    token = os.environ.get("NOTION_TOKEN", "").strip()
    parent_page_id = os.environ.get("PARENT_PAGE_ID", "").strip().replace("-", "")

    if not token:
        print("❌ 请设置环境变量 NOTION_TOKEN", file=sys.stderr)
        sys.exit(1)
    if not parent_page_id:
        print("❌ 请设置环境变量 PARENT_PAGE_ID", file=sys.stderr)
        sys.exit(1)

    print("🚀 开始创建 Notion 个人任务中心…")

    print("  ① 创建「个人任务中心」页面…")
    hub_page_id = create_hub_page(token, parent_page_id)

    print("  ② 创建「任务总表」数据库（5 个字段）…")
    db = create_database(token, hub_page_id)
    database_id = db["id"]
    data_source_id = db["data_sources"][0]["id"]

    print("  ③ 获取字段 ID…")
    prop_ids = get_property_ids(token, data_source_id)

    print("  ④ 重命名默认视图为「全部任务」…")
    rename_default_view(token, database_id)

    print("  ⑤ 创建数据库视图（Timeline / Focus / 回溯 / 统计）…")
    view_urls = create_all_views(token, database_id, data_source_id, prop_ids)

    print("  ⑥ 在主页嵌入免费总览（关联数据库视图）…")
    append_hub_blocks(token, hub_page_id)
    linked_urls = create_linked_overview(token, hub_page_id, data_source_id, prop_ids)
    view_urls.update(linked_urls)

    print("  ⑦ 写入 3 条示例任务…")
    seed_sample_tasks(token, data_source_id)

    hub_url = f"https://www.notion.so/{hub_page_id.replace('-', '')}"
    db_url = db.get("url", f"https://www.notion.so/{database_id.replace('-', '')}")

    print()
    print("✅ 创建完成！")
    print(f"   主页：{hub_url}")
    print(f"   数据库：{db_url}")
    print()
    print("视图直达：")
    for name, url in view_urls.items():
        if url:
            print(f"   {name}: {url}")
    print()
    print("📌 使用提示：")
    print("   • 主页「📊 快速总览」三个关联视图一屏看全局（免费）")
    print("   • 任务标为「已完成」后自动从 Focus / 四象限消失")
    print("   • 每天早上勾选 ☑️今日重点后，在「🔲 四象限矩阵」给任务分象限")
    print("   • 再打开「🎯 Focus 今日重点」盯执行顺序")
    print("   • 每周日复制主页 AI 指令 + 参考「📈 项目统计」生成周报")
    print("   • Timeline 如需按项目分组：Layout → Group by → 项目")


if __name__ == "__main__":
    main()
