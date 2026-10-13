"""Local Chromium login and bounded Feishu operations; no app credentials."""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlparse, parse_qs
import uuid

from bootstrap import runtime_root
from workflow import load, save, verify

SCRIPTS = Path(__file__).resolve().parent
ADAPTER = (SCRIPTS / "page-adapter.js").read_text(encoding="utf-8")


def validate_url(url):
    parsed = urlparse(url)
    host = parsed.hostname or ""
    domains = ("feishu.cn", "larkoffice.com", "larksuite.com")
    if parsed.scheme != "https" or parsed.username or parsed.password or not any(
            host == d or host.endswith("." + d) for d in domains):
        raise ValueError("Use a normal HTTPS Feishu/Lark resource URL without credentials")
    return url


@contextmanager
def browser(headed=False):
    from playwright.sync_api import sync_playwright
    root = runtime_root()
    root.mkdir(parents=True, exist_ok=True)
    profile = root / "browser-profile"
    profile.mkdir(mode=0o700, exist_ok=True)
    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(str(profile), headless=not headed,
                                                       viewport={"width": 1440, "height": 900})
        try:
            yield context, context.pages[0] if context.pages else context.new_page()
        finally:
            context.close()


def ready(page, table_id, timeout=45000):
    page.wait_for_function("""id => {
      const t = window.bitableStore?.modelOperator?.getTableById(id);
      return !!t && t.getLoadedRecordCount() === t.getAllRecordCount() &&
        Array.from(t.getRecordIds()).length === t.getAllRecordCount();
    }""", arg=table_id, timeout=timeout)


def call(page, op, table_id, **kwargs):
    # Explicit arrow wrapper avoids treating a comment-prefixed function as a statement.
    result = page.evaluate("payload => (" + ADAPTER + ")(payload)", {"op": op, "table_id": table_id, **kwargs})
    if not isinstance(result, dict):
        raise RuntimeError("ADAPTER_RETURNED_NO_DATA: stop and inspect the current page")
    return result


def fresh_snapshot(page, table_id):
    page.reload(wait_until="domcontentloaded")
    ready(page, table_id)
    return call(page, "snapshot", table_id)


def drain(page, table_id, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = call(page, "status", table_id)
        if status["localOperationLen"] == 0 and not status["isSubmitting"] and not status["isStoring"]:
            return
        page.wait_for_timeout(200)
    raise RuntimeError("UNKNOWN_SAVE_STATE: reconcile the existing write before submitting anything again")


def apply_plan(page, plan, run_dir):
    """One schema write, one pilot, then a sparse batch. No retry on unknown outcomes."""
    if not plan.get("ready"):
        raise ValueError("Plan has unresolved matches; reconcile it before writing")
    if plan.get("format") != 1:
        raise ValueError("Unsupported plan format")
    run_dir.mkdir(parents=True, exist_ok=False)
    journal = {"status": "starting", "receipts": []}
    journal_path = run_dir / "journal.json"

    def checkpoint(status):
        journal["status"] = status
        # The only deliberately updated file is the current run's journal.
        temp = journal_path.with_suffix(".tmp")
        temp.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(journal_path)

    table_id = plan["table_id"]
    try:
        before = call(page, "snapshot", table_id)
        save(run_dir / "before.json", before)
        save(run_dir / "plan.json", plan)
        checkpoint("before_schema_write")
        response = call(page, "add_options", table_id, plan=plan)
        journal["receipts"].append({"stage": "schema", "response": response})
        checkpoint("schema_submitted")
        drain(page, table_id)
        schema = fresh_snapshot(page, table_id)
        saved_field = next(f for f in schema["fields"] if f["id"] == plan["field_id"])
        choices = saved_field["property"]["options"]
        by_name = {o["name"]: o["id"] for o in choices}
        if any(name not in by_name for name in plan["modules"]):
            raise RuntimeError("Saved schema does not contain the planned modules")
        save(run_dir / "schema-after-refresh.json", schema)
        checkpoint("schema_verified")
        changed = [r for r in plan["records"] if r["changed"]]
        expected = {r["record_id"]: r["old_value"] for r in plan["records"]}
        if changed:
            pilot = changed[0]
            checkpoint("before_pilot_write")
            response = call(page, "set_values", table_id, plan=plan, expected_values=expected,
                            expected_field=saved_field, record_ids=[pilot["record_id"]])
            journal["receipts"].append({"stage": "pilot", "response": response})
            checkpoint("pilot_submitted")
            drain(page, table_id)
            observed = fresh_snapshot(page, table_id)
            actual = next(r for r in observed["records"] if r["id"] == pilot["record_id"])["data"][plan["field_id"]]["value"]
            if actual != by_name[pilot["module"]]:
                raise RuntimeError("Pilot did not persist; stop and reconcile")
            expected[pilot["record_id"]] = actual
            save(run_dir / "pilot-after-refresh.json", observed)
            checkpoint("pilot_verified")
            remaining = [r["record_id"] for r in changed[1:]]
            for start in range(0, len(remaining), 50):
                batch = remaining[start:start + 50]
                checkpoint("before_batch_write")
                response = call(page, "set_values", table_id, plan=plan, expected_values=expected,
                                expected_field=saved_field, record_ids=batch)
                journal["receipts"].append({"stage": "batch", "response": response})
                checkpoint("batch_submitted")
                drain(page, table_id)
                for row in plan["records"]:
                    if row["record_id"] in batch:
                        expected[row["record_id"]] = by_name[row["module"]]
        after = fresh_snapshot(page, table_id)
        save(run_dir / "after-refresh.json", after)
        system = {f["id"] for f in before["fields"] if f["type"] in {1002, 1004}}
        result = verify(plan, before, after, system)
        save(run_dir / "verification.json", result)
        checkpoint("verified" if result["passed"] else "verification_failed")
        if not result["passed"]:
            raise RuntimeError("Verification found a mismatch; inspect the run without retrying")
        return result
    except Exception:
        if journal["status"] != "verification_failed":
            checkpoint("needs_reconciliation")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    p = sub.add_parser("login"); p.add_argument("--url", required=True)
    p.add_argument("--wait-seconds", type=int, default=300)
    for command in ("read", "export-sheet"):
        p = sub.add_parser(command); p.add_argument("--url", required=True)
        p.add_argument("--output", required=True); p.add_argument("--headed", action="store_true")
        if command == "read": p.add_argument("--table-id")
    p = sub.add_parser("apply"); p.add_argument("--plan", required=True)
    p.add_argument("--commit", action="store_true", help="Perform the explicitly authorized plan")
    p.add_argument("--run-dir"); p.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    if args.command == "doctor":
        with browser() as (_, page):
            page.set_content("<title>Feishu skill runtime check</title><p>local-only</p>")
            assert page.title() == "Feishu skill runtime check"
        print(json.dumps({"browser_started": True, "feishu_access_verified": False}))
        return
    if args.command == "apply":
        plan = load(args.plan)
        if not args.commit:
            print(json.dumps({"dry_run": True, "ready": plan.get("ready"), "changes": plan.get("change_count"),
                              "new_modules": plan.get("new_modules")}, ensure_ascii=False))
            return
        url = validate_url(plan["target_url"])
        table_id = plan["table_id"]
    else:
        url = validate_url(args.url)
        table_id = getattr(args, "table_id", None) or parse_qs(urlparse(url).query).get("table", [None])[0]
    if args.command == "read" and not table_id:
        raise ValueError("Provide the actual data table's ID; a wiki token is not a table ID")
    with browser(headed=args.command == "login" or getattr(args, "headed", False)) as (_, page):
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if args.command == "login":
            print("Log in in this Chromium window with an account that can access the target resource.", flush=True)
            page.wait_for_function("() => !!window.bitableStore?.modelOperator || !!window.spread?.sheets?.length",
                                   timeout=args.wait_seconds * 1000)
            print("Resource runtime loaded. Run read to verify the selected table and full record access.")
        elif args.command == "export-sheet":
            output = Path(args.output).expanduser()
            if output.exists(): raise ValueError("Source export destination already exists")
            page.get_by_text("菜单", exact=True).click()
            page.get_by_role("menuitem", name="表格", exact=True).hover()
            page.get_by_text("下载为", exact=True).hover()
            with page.expect_download(timeout=60000) as download:
                page.get_by_text("本地 Excel 表格(.xlsx)", exact=True).click()
            output.parent.mkdir(parents=True, exist_ok=True)
            download.value.save_as(str(output))
            print("Source workbook downloaded; the source was not edited.")
        else:
            ready(page, table_id)
            if args.command == "read":
                result = call(page, "snapshot", table_id)
                save(args.output, result)
                print(json.dumps({"record_count": result["recordCount"], "snapshot_saved": True}))
            else:
                run_dir = Path(args.run_dir).expanduser() if args.run_dir else runtime_root() / "runs" / str(uuid.uuid4())
                result = apply_plan(page, plan, run_dir)
                print(json.dumps({"verified": result["passed"], "matched": result["matched"], "run_dir": str(run_dir)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Stopped ({type(error).__name__}): {str(error).splitlines()[0]}", file=sys.stderr)
        print("Do not retry an uncertain write. Inspect the saved journal and refresh the target first.", file=sys.stderr)
        raise SystemExit(1)
