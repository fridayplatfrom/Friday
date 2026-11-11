import sys
import argparse
import traceback
import logging

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

from tiny_experts.web.server import run_server

def main():
    parser = argparse.ArgumentParser(description="Tiny Expert AI System: Interactive Web UI")
    parser.add_argument("--port", type=int, default=8000, help="Local port to bind HTTP server (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser")
    args = parser.parse_args()

    while True:
        try:
            run_server(port=args.port, open_browser=not args.no_browser)
            break
        except (KeyboardInterrupt, SystemExit):
            print("\n[SYSTEM] Server stopped by user.")
            break
        except Exception as exc:
            print(f"[ERROR] Server stopped with error: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            import time
            time.sleep(1)

if __name__ == "__main__":
    main()
