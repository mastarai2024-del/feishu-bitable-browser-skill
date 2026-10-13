"""Install only this original skill; never silently overwrite an existing copy."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=Path.home() / ".agents" / "skills")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    source = Path(__file__).resolve().parent / "skills" / "feishu-bitable-browser"
    target = args.destination.expanduser().resolve() / source.name
    if target.exists():
        if not args.replace:
            raise SystemExit("Skill already exists. Review it; use --replace only for an authorized update.")
        runtime = Path(os.environ.get("FEISHU_SKILL_RUNTIME", str(Path.home() / ".cache" / "feishu-bitable-browser")))
        backup = runtime / "skill-backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(target, backup)
        if target.is_symlink(): target.unlink()
        else: shutil.rmtree(target)
        print("Previous skill backed up:", backup)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    print("Installed:", target)
    print("Invoke $feishu-bitable-browser. If it is not visible, restart your agent.")


if __name__ == "__main__":
    main()
