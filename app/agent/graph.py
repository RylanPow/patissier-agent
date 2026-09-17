import asyncio
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings
from app.agent.mcp_client import get_mcp_tools
from app.agent.rag import search_food_knowledge

async def run_chat_loop():
    print("Booting up Patissier Agent...")
    print("Connecting to FastMCP Subprocess...")

    # connect to MCP Server and get the live tools
    async with get_mcp_tools as mcp_tools:
        # connect the local RAG tool with remote MCP tools
        all_tools = [search_food_knowledge] + mcp_tools
        print(f"loaded {len(all_tools)} tools")

        # init LLM
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key = settings.OPEN_API_KEY,
            temperature = 0.2
        )

        #i init conversation memory
        memory = MemorySaver()
        system_prompt = (
            "You are Patissier, an advanced enterprise food intelligence agent."
            "You have access to internal qualitative knowledge via RAG (search_food_knowledge) "
            "and live quantitative/weather data via MCP tools (get_trend_velocity, check_crop_weather). "
            "Always think step by step. If a user asks about a food trend, try to back up your claims "
            "with both qualitative context and hard velocity numbers. Be concise, professional, and analytical."
        )

        config = {"configurable" : {"thread_id" : "patissier-session-1"}}

        print("\n" + "="*50)
        print("Patissier is ready! Type 'exit' to quit.")
        print("="*50)

        # interactive CLI chat loop

        while True:
            try:
                user_input = input("\nYou: ")
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("Shutting down Patissier...")
                    break
                    
                if not user_input.strip():
                    continue
                    
                inputs = {"messages": [("user", user_input)]}
                print("\n Thinking...")
                
                # keep track of printed message IDs so we don't double-print during stream updates
                printed_ids = set()
                
                # stream the state graph updates to watch the agent reason in real-time
                async for chunk in agent_executor.astream(inputs, config=config, stream_mode="values"):
                    message = chunk["messages"][-1]
                    
                    if hasattr(message, "id") and message.id in printed_ids:
                        continue
                    if hasattr(message, "id"):
                        printed_ids.add(message.id)
                    
                    # intercept and print Tool Calls
                    if message.type == "ai" and message.tool_calls:
                        for tc in message.tool_calls:
                            print(f"  [Tool Call] {tc['name']} -> {tc['args']}")
                    
                    # intercept and print Tool Results
                    elif message.type == "tool":
                         print(f"  [Tool Result] Data received from {message.name}")
                    
                    # print the final AI Response
                    elif message.type == "ai" and message.content:
                        print(f"\nPatissier: {message.content}")
                        
            except KeyboardInterrupt:
                print("\nShutting down Patissier...")
                break
            except Exception as e:
                print(f"\nError during execution: {e}")

if __name__ == "__main__":
    asyncio.run(run_chat_loop())
                