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
    
@mcp.tool()
async def check_crop_weather(region_name: str, latitude: float, longitude: float) -> str:
    # live weather conditions and short term agircultural forecastst for a crop-growing region
    # useful for assessing yield risk, frost conditions, drought impact, etc on raw ingredients
    # args: 
    # region_name: descriptive name of the region e.g. Bronte, Sicily
    # latitude and longitude: coordinates of the growing region
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ["temperature_2m", "relative_humidity_2m", "precipitation"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "timezone": "auto",
        "forecast_days": 3,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        current = data.get("current", {})
        daily = data.get("daily", {})

        curr_temp = current.get("temperature_2m", "N/A")
        curr_humidity = current.get("relative_humidity_2m", "N/A")
        curr_precip = current.get("precipitation", 0.0)

        # 3-day outlook summary
        min_temps = daily.get("temperature_2m_min", [])
        max_temps = daily.get("temperature_2m_max", [])
        precip_sums = daily.get("precipitation_sum", [])

        forecast_lines = []
        for i in range(len(min_temps)):
            forecast_lines.append(
                f"  • Day {i+1}: Min {min_temps[i]}°C / Max {max_temps[i]}°C | Rain {precip_sums[i]} mm"
            )

        return (
            f"Weather Report for {region_name} (Lat: {latitude}, Lon: {longitude}):\n"
            f"- Current Temperature: {curr_temp}°C\n"
            f"- Relative Humidity: {curr_humidity}%\n"
            f"- Current Precipitation: {curr_precip} mm\n"
            f"- 3-Day Forecast:\n" + "\n".join(forecast_lines)
        )

    except Exception as e:
        return f"Unable to retrieve weather data for {region_name}: {str(e)}"

if __name__ == "__main__":
    print("Starting FastMCP server...", flush=True)
    mcp.run()