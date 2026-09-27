import argparse
import os
import uvicorn


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run YouTube Audio Extractor")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 8765)),
        help="Port to bind the server to (default: 8765)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("HOST", "127.0.0.1"),
        help="Host to bind the server to (default: 127.0.0.1)",
    )
    args = parser.parse_args()

    print(f"Launching YouTube Audio Extractor on http://{args.host}:{args.port} ...")
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=True)

