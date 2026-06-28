"""LINE Messaging API で push 通知を送る。

LINE Notify は 2025-03 で終了したため、Messaging API の push を使う。
必要な環境変数:
    LINE_CHANNEL_ACCESS_TOKEN : Messaging API チャネルのアクセストークン（長期）
    LINE_USER_ID              : 送信先の userId（自分の userId、または groupId）

どちらも未設定なら send_line() は何もせず False を返す（CI を壊さない）。
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error

PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"


def send_line(text: str, *, token: str | None = None, to: str | None = None) -> bool:
    """LINE に push メッセージを1通送る。成功で True。

    token / to が未指定なら環境変数から読む。
    どちらか欠けていれば送信せず False（ログのみ）。
    """
    token = token or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    to = to or os.environ.get("LINE_USER_ID", "").strip()

    if not token or not to:
        print("[notifier] LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID が未設定のため送信スキップ")
        return False

    payload = json.dumps({
        "to": to,
        "messages": [{"type": "text", "text": text[:4900]}],  # LINE上限5000字
    }).encode("utf-8")

    req = urllib.request.Request(
        PUSH_ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = 200 <= resp.status < 300
            print(f"[notifier] LINE送信 status={resp.status}")
            return ok
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"[notifier] LINE送信失敗 HTTP {e.code}: {body}")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"[notifier] LINE送信失敗: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    # 動作確認用: python src/notifier.py "テストメッセージ"
    import sys
    msg = sys.argv[1] if len(sys.argv) > 1 else "🛁 suiテスト通知です（届けばOK）"
    ok = send_line(msg)
    print("結果:", "送信成功" if ok else "未送信/失敗")
