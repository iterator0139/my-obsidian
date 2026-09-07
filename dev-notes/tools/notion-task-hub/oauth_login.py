#!/usr/bin/env python3
"""
Notion OAuth 2.0 本地登录 — 换取 access_token 供 setup 脚本使用。

环境变量：
  OAUTH_CLIENT_ID      Developer portal → Configuration → OAuth client ID
  OAUTH_CLIENT_SECRET  Developer portal → Configuration → OAuth client secret
  OAUTH_REDIRECT_URI   与 portal 里注册的 Redirect URI 完全一致（默认 http://localhost:8765/callback）

用法：
  export OAUTH_CLIENT_ID="..."
  export OAUTH_CLIENT_SECRET="..."
  python3 oauth_login.py

成功后 token 写入同目录 .notion_token（已 gitignore 建议），并打印到终端。
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

DEFAULT_REDIRECT = "http://localhost:8765/callback"
TOKEN_FILE = Path(__file__).parent / ".notion_token"


def exchange_code(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict:
    cred = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    req = urllib.request.Request(
        "https://api.notion.com/v1/oauth/token",
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "Authorization": f"Basic {cred}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Token exchange failed ({e.code}): {e.read().decode()}") from e


def build_auth_url(client_id: str, redirect_uri: str) -> str:
    params = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "owner": "user",
        }
    )
    return f"https://api.notion.com/v1/oauth/authorize?{params}"


def main() -> None:
    client_id = os.environ.get("OAUTH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("OAUTH_CLIENT_SECRET", "").strip()
    redirect_uri = os.environ.get("OAUTH_REDIRECT_URI", DEFAULT_REDIRECT).strip()

    if not client_id or not client_secret:
        print("❌ 请设置 OAUTH_CLIENT_ID 和 OAUTH_CLIENT_SECRET", file=sys.stderr)
        sys.exit(1)

    parsed = urllib.parse.urlparse(redirect_uri)
    if parsed.hostname != "localhost" or not parsed.port:
        print(
            "⚠️  建议使用 http://localhost:PORT/callback 作为本地 redirect URI",
            file=sys.stderr,
        )

    result: dict | None = None
    error_msg: str | None = None

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            nonlocal result, error_msg
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

            if "error" in qs:
                error_msg = qs["error"][0]
                self._respond(f"<h2>授权失败：{error_msg}</h2><p>可关闭此页</p>")
                return

            code = qs.get("code", [None])[0]
            if not code:
                self._respond("<h2>未收到 code</h2>")
                error_msg = "missing_code"
                return

            try:
                result = exchange_code(client_id, client_secret, code, redirect_uri)
                self._respond(
                    "<h2>✅ 授权成功</h2>"
                    "<p>可以关闭此页面，回到终端继续操作。</p>"
                )
            except RuntimeError as e:
                error_msg = str(e)
                self._respond(f"<h2>换取 token 失败</h2><pre>{e}</pre>")

        def _respond(self, html: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())

        def log_message(self, fmt: str, *args: object) -> None:
            pass  # 静默 HTTP 日志

    port = parsed.port or 8765
    server = HTTPServer(("localhost", port), CallbackHandler)

    auth_url = build_auth_url(client_id, redirect_uri)
    print("🔐 正在打开 Notion 授权页面…")
    print(f"   {auth_url}")
    print()
    print("📌 授权时请注意：")
    print("   1. 选择要安装的工作区")
    print("   2. 在页面选择器里勾选「父页面」及其子页面（或选顶层页面）")
    print("   3. 点击「允许访问」")
    print()

    Thread(target=server.handle_request, daemon=True).start()
    webbrowser.open(auth_url)
    server.handle_request()  # 等待第二次请求（部分浏览器会预检）

    if error_msg:
        print(f"❌ {error_msg}", file=sys.stderr)
        sys.exit(1)
    if not result:
        print("❌ 未获取到 token", file=sys.stderr)
        sys.exit(1)

    access_token = result["access_token"]
    TOKEN_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print("✅ 授权成功！")
    print(f"   工作区：{result.get('workspace_name', '—')}")
    print(f"   workspace_id：{result.get('workspace_id', '—')}")
    print(f"   token 已保存：{TOKEN_FILE}")
    print()
    print("下一步：")
    print(f'  export NOTION_TOKEN="$(python3 -c \'import json; print(json.load(open("{TOKEN_FILE}"))["access_token"])\')"')
    print('  export PARENT_PAGE_ID="你授权时勾选的父页面ID"')
    print('  python3 setup_notion_task_hub.py')


if __name__ == "__main__":
    main()
