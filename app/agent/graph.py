import asyncio
import logging
from typing import Literal

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings
from app.agent.mcp_client import get_mcp_tools
from app.agent.rag import search_food_knowledge
from app.agent.state import PatissierState, SupervisorRouter
from app.agent.prompts import (
    SUPERVISOR_PROMPT, 
    MARKET_SPECIALIST_PROMPT, 
    FORMULATION_SPECIALIST_PROMPT, 
    SYNTHESIZER_PROMPT
)

# mute LangChain/Gemini schema warnings
logging.getLogger("langchain_google_genai._function_utils").setLevel(logging.ERROR)

def extract_text_from_content(content) -> str:
    """Helper to parse Gemini's content blocks into clean text."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list) and len(content) > 0:
        if isinstance(content[0], dict) and "text" in content[0]:
            return content[0]["text"]
    return str(content)

async def run_chat_loop():
    print(" Booting up Patissier Multi-Agent System...")
    
    async with get_mcp_tools() as mcp_tools:
        # 1. split tools into specialist domains
        market_tool_names = ["get_trend_velocity", "check_crop_weather"]
        formulation_tool_names = ["check_fda_gras", "find_ingredient_substitutes"]
        
        market_tools = [t for t in mcp_tools if t.name in market_tool_names]
        formulation_tools = [search_food_knowledge] + [t for t in mcp_tools if t.name in formulation_tool_names]
        
        print(f"Loaded {len(market_tools)} Market tools and {len(formulation_tools)} Formulation tools.")
        
        # 2. initialize Gemini
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.6-flash", 
            google_api_key=settings.GOOGLE_API_KEY, 
            temperature=1
        )

        # specialist subgraph factory
        def create_specialist_graph(specialist_prompt: str, tools: list):
            """Creates an isolated ReAct StateGraph for a specialist"""
            llm_with_tools = llm.bind_tools(tools)
            
            def call_model(state: MessagesState):
                messages = state["messages"]
                if not any(isinstance(m, SystemMessage) for m in messages):
                    messages = [SystemMessage(content=specialist_prompt)] + messages
                response = llm_with_tools.invoke(messages)
                return {"messages": [response]}
                
            def should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
                if state["messages"][-1].tool_calls:
                    return "tools"
                return "__end__"
                
            workflow = StateGraph(MessagesState)
            workflow.add_node("agent", call_model)
            workflow.add_node("tools", ToolNode(tools))
            workflow.add_edge(START, "agent")
            workflow.add_conditional_edges("agent", should_continue, ["tools", "__end__"])
            workflow.add_edge("tools", "agent")
            return workflow.compile()

        # compile the two sub-graphs
        market_graph = create_specialist_graph(MARKET_SPECIALIST_PROMPT, market_tools)
        formulation_graph = create_specialist_graph(FORMULATION_SPECIALIST_PROMPT, formulation_tools)

        # main supervisor graph nodes
        async def supervisor_node(state: PatissierState):
            print("  [System] Supervisor assessing routing logic...")
            supervisor_llm = llm.with_structured_output(SupervisorRouter)

            # grab the original user objective
            original_user_msg = next(
                (m.content for m in state["messages"] if isinstance(m, HumanMessage) or getattr(m, "type", "") == "human"),
                "No objective found"
            )

            status = (
                f"Market Research: {'Collected' if state.get('market_research') else 'Not yet collected'}\n"
                f"Formulation & Compliance: {'Collected' if state.get('formulation_compliance') else 'Not yet collected'}"
            )

            sys_msg = SystemMessage(content=SUPERVISOR_PROMPT + f"\n\nCURRENT PROGRESS:\n{status}")
            routing_prompt = HumanMessage(
                content=f"User Objective: {original_user_msg}\n\nGiven the current progress above, determine the next node to run."
            )

            decision = await supervisor_llm.ainvoke([sys_msg, routing_prompt])
            print(f"  [System] Supervisor decided next step: {decision.next_node}")
            return {"next_node": decision.next_node}


        async def market_node(state: PatissierState):
            print("  [System] Executing Market Specialist Sub-Graph...")
            result = await market_graph.ainvoke({"messages": state["messages"]})
            final_text = extract_text_from_content(result["messages"][-1].content)
            
            # save findings to the scratchpad AND append a summary to the main thread
            return {
                "market_research": final_text,
            }

        async def formulation_node(state: PatissierState):
            print("  [System] Executing Formulation Specialist Sub-Graph...")
            result = await formulation_graph.ainvoke({"messages": state["messages"]})
            final_text = extract_text_from_content(result["messages"][-1].content)
            
            return {
                "formulation_compliance": final_text,
            }

        async def synthesizer_node(state: PatissierState):
            print("  [System] Synthesizer drafting executive report...")
            sys_msg = SystemMessage(content=SYNTHESIZER_PROMPT)
            findings = (
                f"### Market Data\n{state.get('market_research', 'Not collected')}\n\n"
                f"### Formulation Data\n{state.get('formulation_compliance', 'Not collected')}"
            )
            
            user_goal = next(
                (m.content for m in state["messages"] if isinstance(m, HumanMessage) or getattr(m, "type", "") == "human"),
                ""
            )
            
            prompt = [
                sys_msg,
                HumanMessage(content=f"User Goal: {user_goal}\n\nSynthesize the following collected intelligence:\n{findings}")
            ]
            
            response = await llm.ainvoke(prompt)
            return {"messages": [response]}

        # ~~~MAIN GRAPH~~
        def supervisor_router(state: PatissierState) -> str:
            # map the Pydantic structured output directly to the node names
            return state["next_node"]

        workflow = StateGraph(PatissierState)
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("market_specialist", market_node)
        workflow.add_node("formulation_specialist", formulation_node)
        workflow.add_node("synthesizer", synthesizer_node)

        workflow.add_edge(START, "supervisor")
        workflow.add_conditional_edges(
            "supervisor", 
            supervisor_router, 
            {
                "market_specialist": "market_specialist",
                "formulation_specialist": "formulation_specialist",
                "synthesizer": "synthesizer"
            }
        )
        
        # specialists always report back to the supervisor when finished
        workflow.add_edge("market_specialist", "supervisor")
        workflow.add_edge("formulation_specialist", "supervisor")
        workflow.add_edge("synthesizer", END)
        
        memory = MemorySaver()
        agent_executor = workflow.compile(checkpointer=memory)
        config = {"configurable": {"thread_id": "patissier-multi-agent-1"}}
        
        print("\n" + "="*50)
        print("Patissier Supervisor Architecture is ready! Type 'exit' to quit.")
        print("="*50)
        
        # ~~~~~~~~~~~~~ CLI MAIN LOOP.  change to FastAPI backend later ~~~~~~~~~~~~~~ #
        while True:
            try:
                user_input = input("\nYou: ")
                if user_input.lower() in ['exit', 'quit', 'q']:
                    break
                if not user_input.strip():
                    continue
                    
                print("\n Processing...")
                
                # stream the main graph updates (we will see the System print statements trigger)
                async for chunk in agent_executor.astream({"messages": [("user", user_input)]}, config=config, stream_mode="updates"):
                    # only care about printing the final synthesizer output to the user
                    if "synthesizer" in chunk:
                        message = chunk["synthesizer"]["messages"][-1]
                        clean_text = extract_text_from_content(message.content)
                        print(f"\nPatissier: {clean_text}")
                            
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\n Error during execution: {e}")

if __name__ == "__main__":
    asyncio.run(run_chat_loop())