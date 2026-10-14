"""Local service; run from the project root with Python 3.11."""
import argparse
import os
import secrets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--cert")
    parser.add_argument("--key")
    args = parser.parse_args()
    os.environ.setdefault("EDGEAI_TOKEN", secrets.token_urlsafe(24))
    print("\nPAIRING TOKEN (trusted devices only): " + os.environ["EDGEAI_TOKEN"], flush=True)
    print("Camera images stay on this machine; initial model download requires internet.", flush=True)
    print("Phone browser camera requires trusted HTTPS. IP Webcam/MJPEG is the simpler LAN fallback.\n", flush=True)
    from edgeai.server import create_app
    import uvicorn
    uvicorn.run(create_app(), host=args.host, port=args.port,
                ssl_certfile=args.cert, ssl_keyfile=args.key, access_log=False)

if __name__ == "__main__":
    main()
