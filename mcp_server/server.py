import httpx
from fastmcp import FastMCP
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models import Trend

mcp = FastMCP("Patissier Tools")

@mcp.tool()
def get_trend_velocity(ingredient: str) -> str:

    # Retrieve quantitative velocity metrics for a specific food ingredient or product.
    # Returns 30-day volume, growth percentage, category, and target geographic focus.
    
    with SessionLocal() as session:
        # Case-insensitive partial match to make agent querying more forgiving
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