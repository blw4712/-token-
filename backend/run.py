"""启动本地 API，并把端口写到可被 Electron 读取的文件。

用法：
    python backend/run.py
    python backend/run.py --port 8765
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

from app.config import DATA_DIR, SERVER_PATH  # noqa: E402


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def write_server_file(port: int) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SERVER_PATH.write_text(
        json.dumps(
            {
                "port": port,
                "url": f"http://127.0.0.1:{port}",
                "pid": os.getpid(),
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent Console 本地接口")
    parser.add_argument("--port", type=int, default=0, help="0 表示随机端口")
    parser.add_argument("--reload", action="store_true", help="开发时自动重载")
    args = parser.parse_args()

    port = args.port or free_port()
    write_server_file(port)

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="warning",
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
