"""python -m harness <command>. Commands: screen, run, diff, confirm, keep, revert, gate, validate, report-check, index, pack-check, status."""
import importlib
import sys

COMMANDS = {
    "screen": "screening", "run": "run", "diff": "diff", "confirm": "confirm", "keep": "keep", "revert": "keep",
    "gate": "gate", "validate": "validate", "report-check": "report_check", "index": "index", "pack-check": "pack_check",
    "status": "status",
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help") or argv[0] not in COMMANDS:
        print(__doc__)
        return 0 if (not argv or argv[0] in ("-h", "--help")) else 2
    cmd, rest = argv[0], argv[1:]
    from .envfile import load_env
    load_env()
    mod = importlib.import_module(f"harness.{COMMANDS[cmd]}")
    if cmd == "revert":
        return mod.main_revert(rest)
    return mod.main(rest) or 0


if __name__ == "__main__":
    sys.exit(main())
