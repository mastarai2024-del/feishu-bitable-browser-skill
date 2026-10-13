"""Install a private runtime without changing the system Python or agent config."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import venv


def runtime_root():
    return Path(os.environ.get("FEISHU_SKILL_RUNTIME", str(Path.home() / ".cache" / "feishu-bitable-browser"))).expanduser().resolve()


def python_path(root):
    return root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-browser", action="store_true", help="Install Python packages only; browser doctor will still be required")
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        raise SystemExit("Use Python 3.11 or newer.")
    root = runtime_root()
    root.mkdir(parents=True, exist_ok=True)
    interpreter = python_path(root)
    if not interpreter.exists():
        venv.EnvBuilder(with_pip=True).create(root / "venv")
    req = Path(__file__).with_name("requirements.txt")
    subprocess.run([str(interpreter), "-m", "pip", "install", "-r", str(req)], check=True)
    if not args.skip_browser:
        subprocess.run([str(interpreter), "-m", "playwright", "install", "chromium"], check=True)
    print('Runtime installed. Next: python "' + str(Path(__file__).with_name("run.py").resolve()) + '" doctor')
    print("Runtime:", root)
    print("This confirms installation only, not Feishu access.")


if __name__ == "__main__":
    main()
