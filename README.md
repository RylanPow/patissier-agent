### Patissier Agent
An agentic food development platform to gather consumer insights, commodity price predictions, and supplier quotes.

Run multi-agent graphy.py: uv run python -m app.agent.graph

launch fresh docker container:
docker run -d \
  --name food-agent-db \
  --restart unless-stopped \
  -e POSTGRES_USER= \
  -e POSTGRES_PASSWORD= \
  -e POSTGRES_DB= \
  -p 1111:1111 \
  pgvector/pgvector:pg16