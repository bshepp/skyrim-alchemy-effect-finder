import argparse, threading, webbrowser
import uvicorn
from alchemy_helper.web.app import create_app

def main():
    ap = argparse.ArgumentParser(prog="alchemy_helper")
    ap.add_argument("--port", type=int, default=8712)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    if not args.no_browser:
        threading.Timer(
            1.0, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")).start()
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port)

if __name__ == "__main__":
    main()
