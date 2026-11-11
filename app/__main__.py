"""`python -m app` serves the chat UI at /, the dashboard at /dashboard and the API at /api (port 8000)."""
import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app", description=__doc__)
    parser.add_argument("--host", default=os.environ.get("DW_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("DW_PORT", "8000")))
    args = parser.parse_args()
    mode = "test mode ON (X-Test-Principal accepted with the exam token)" if os.environ.get("DW_TEST_MODE") == "1" \
        else "test mode off"
    print(f"Chat UI   http://{args.host}:{args.port}/\nDashboard http://{args.host}:{args.port}/dashboard\n{mode}",
          flush=True)
    uvicorn.run("app.adapters.chat:app", host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
