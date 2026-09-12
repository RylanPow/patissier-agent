import httpx
from fastmcp import FastMCP
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models import Trend

mcp = FastMCP("Patissier Tools")

if __name__ == "__main__":
    print("Starting FastMCP server...", flush=True)
    mcp.run()