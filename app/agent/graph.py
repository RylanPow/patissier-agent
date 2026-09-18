import asyncio
from typing import Literal

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings
from app.agent.mcp_client import get_mcp_tools
from app.agent.rag import search_food_knowledge

async def run_chat_loop():
    print("Booting up Patissier Agent...")

    # connect to MCP Server and get the live tools
    async with get_mcp_tools() as mcp_tools:
        # connect the local RAG tool with remote MCP tools
        all_tools = [search_food_knowledge] + mcp_tools
        print(f"loaded {len(all_tools)} tools")

        # init LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.8-flash",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature = 1.0
        )
        llm_with_tools = llm.bind_tools(all_tools)

        #i init conversation memory
        system_prompt = SystemMessage(
            content="You are Patissier, an advanced enterprise food intelligence agent."
            "You have access to internal qualitative knowledge via RAG (search_food_knowledge) "
            "and live quantitative/weather data via MCP tools (get_trend_velocity, check_crop_weather). "
            "Always think step by step. If a user asks about a food trend, try to back up your claims "
            "with both qualitative context and hard velocity numbers. Be concise, professional, and analytical."
        )


        # define graph nodes
        def call_model(state: MessagesState):
            response = llm_with_tools.invoke(state["messages"])
            return {"messages" : [response]}
        
        # routing logic
        def should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
            last_message = state["messages"][-1]
            if last_message.tool_calls:
                return "tools"
            return "__end__"
        
        # ~~~~~~~~~~ Construct the State Graph ~~~~~~~~~~~
        workflow = StateGraph(MessagesState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(all_tools))

        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", should_continue, ["tools", END])
        workflow.add_edge("tools", "agent")

        memory = MemorySaver()
        agent_executor = workflow.compile(checkpointer=memory)
        config = {"configurable": {"thread_id" : "patissier-session-1"}}

        print("\n" + "="*50)
        print("Patissier explicit StateGraph is ready! Type 'exit' to quit.")
        print("="*50)

        is_first_turn = True

        while True:
            try:
                user_input = input("\nYou: ")
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("Shutting down Patissier...")
                    break
                    
                if not user_input.strip():
                    continue
                    
                print("\n Thinking...")
                # keep track of printed message IDs so we don't double-print during stream updates
               
                if is_first_turn:
                    messages_to_send = [system_prompt, ("user", user_input)]
                    is_first_turn = False
                else:
                    messages_to_send = [("user", user_input)]
                
                # stream the state graph updates to watch the agent reason in real-time
                async for chunk in agent_executor.astream({"messages": [("user", user_input)]}, config=config, stream_mode="updates"):
                    # chuhnk is keyed by the node name that just finished (e.g. "agent" or "tools")
                    for node_name, node_state in chunk.items():
                        message = node_state["messages"][-1]

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
                