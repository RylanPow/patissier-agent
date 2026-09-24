from typing import Annotated, List, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

class PatissierState(TypedDict):
    """Core state for the Supervisor-Specialist Multi-Agent Graph."""
    # append-only message history for the conversational thread
    messages: Annotated[List[BaseMessage], add_messages]
    
    # internal agent scratchpads for handoffs
    market_research: Optional[str]
    formulation_compliance: Optional[str]
    
    # explicit routing control
    next_node: Optional[str]

    #iteration saftey guardrail so supervisor doesn't doomloop and burn tokens
    supervisor_iterations: Optional[int] 

class SupervisorRouter(BaseModel):
    """Pydantic schema for structured supervisor routing decisions."""
    next_node: str = Field(
        description="The next node to execute. Must be one of: 'market_specialist', 'formulation_specialist', or 'synthesizer'."
    )
    task_instructions: str = Field(
        description="Specific delegated instructions or sub-queries for the chosen specialist."
    )