"""Launcher for packaging IP³ as a Windows executable (PyInstaller).

Starts a local Streamlit server for ``app.py`` and opens the default browser.
For day-to-day use, ``run_ip3.bat`` is the recommended entry point; this
launcher exists so ``build_exe.bat`` can produce ``dist/IP3.exe``.
"""
from __future__ import annotations

import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    app_path = base_dir / "app.py"
    port = "8501"
    url = f"http://localhost:{port}"

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.port",
            port,
            "--server.headless",
            "true",
        ]
    )
    time.sleep(2)
    try:
        webbrowser.open(url)
    except Exception:
        print(f"브라우저를 열 수 없습니다. 직접 접속하세요: {url}")
    print(f"IP3 실행 중: {url}")
    print("종료하려면 이 창을 닫거나 Ctrl+C 를 누르세요.")
    process.wait()


if __name__ == "__main__":
    main()
