import httpx
from fastmcp import FastMCP
from sqlalchemy import select

from pathlib import Path
import sys
# add project root directory to sys.path so 'app' imports resolve regardless of how this script is called
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


from app.db.session import SessionLocal
from app.db.models import Trend

mcp = FastMCP("Patissier Tools")

@mcp.tool()
def get_trend_velocity(ingredient: str) -> str:

    # Retrieve quantitative velocity metrics for a specific food ingredient or product.
    # Returns 30-day volume, growth percentage, category, and target geographic focus.
    
    with SessionLocal() as session:
        query = select(Trend).where(Trend.ingredient_name.ilike(f"%{ingredient.strip()}%"))
        trend = session.scalar(query)

        if not trend:
            return f"No trend data found for '{ingredient}' in patissier_db."
        return (
            f"Trend Analysis for {trend.ingredient_name}:\n"
            f"- Category: {trend.category}\n"
            f"- 30-Day Search/Mention Volume: {trend.volume_30d:,}\n"
            f"- Growth Rate: {trend.growth_pct}%\n"
            f"- Primary Geographic Focus: {trend.geo_focus or 'Global'}\n"
            f"- Last Updated: {trend.updated_at.strftime('%Y-%m-%d') if trend.updated_at else 'N/A'}"
        )

if __name__ == "__main__":
    print("Starting FastMCP server...", flush=True)
    mcp.run()