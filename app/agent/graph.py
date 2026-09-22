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

# mute langchain/gemini schema warning
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
    print("Booting up Patissier Multi-Agent System...")
    
    async with get_mcp_tools() as mcp_tools:
        # split tools into specialist domains
        market_tool_names = ["get_trend_velocity", "check_crop_weather"]
        formulation_tool_names = ["check_fda_gras", "find_ingredient_substitutes"]
        
        market_tools = [t for t in mcp_tools if t.name in market_tool_names]
        formulation_tools = [search_food_knowledge] + [t for t in mcp_tools if t.name in formulation_tool_names]
        
        print(f"Loaded {len(market_tools)} Market tools and {len(formulation_tools)} Formulation tools.")
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.8-flash", 
            google_api_key=settings.GOOGLE_API_KEY, 
            temperature=1
        )

    def create_specialist_graph(specialist_prompt: str, tools: list):
        """creates an isolated ReAct StateGraph for a specialist"""
        llm_with_tools = llm.bind_tools(tools)

        def call_model(state: MessagesState):
            messages = state["messages"]
            if not any(isinstance(m, SystemMessage) for m in messages):
                messages = [SystemMessage(content=specialist_prompt)] + messages
            response = llm_with_tools.invoke(messages)
            return {"messages" : [response]}
        
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