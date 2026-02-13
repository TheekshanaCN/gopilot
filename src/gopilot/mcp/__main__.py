from __future__ import annotations

import argparse

from gopilot.mcp.server import build_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GoPilot MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport to use",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for network transports")
    parser.add_argument("--port", type=int, default=8765, help="Port for network transports")
    args = parser.parse_args()

    mcp = build_server()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
