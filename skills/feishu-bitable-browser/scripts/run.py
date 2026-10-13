"""Portable entry point for the private runtime."""
import os
from pathlib import Path
import sys
from bootstrap import python_path, runtime_root


def main():
    interpreter = python_path(runtime_root())
    if not interpreter.exists():
        raise SystemExit("Runtime missing. Run bootstrap.py first.")
    scripts = Path(__file__).resolve().parent
    argv = sys.argv[1:]
    if not argv:
        raise SystemExit("Commands: doctor, login, read, export-sheet, apply, map, verify, test")
    if argv[0] == "test":
        tests = scripts.parents[2] / "tests"
        if not tests.is_dir():
            raise SystemExit("Tests live in the source repository. Clone it and run this command there.")
        os.execv(str(interpreter), [str(interpreter), "-X", "utf8", "-m", "unittest", "discover", "-s", str(tests), "-v"])
    module = "workflow.py" if argv[0] in {"map", "verify"} else "browser.py"
    os.execv(str(interpreter), [str(interpreter), "-X", "utf8", str(scripts / module), *argv])


if __name__ == "__main__":
    main()
