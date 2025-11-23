from __future__ import annotations
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from typing_extensions import TypedDict

from src.flow_agent.logging_config import setup_logging
from src.flow_agent.utils.nodes import call_combiner_model, call_summarizer_model
from src.flow_agent.utils.state import State

setup_logging()


class Context(TypedDict):
    my_configurable_param: str


# this name is mentioned in langgraph.json
graph = (
    StateGraph(State, context_schema=Context)
    .add_node("summarizer", call_summarizer_model)
    .add_node("combiner", call_combiner_model)
    .add_edge(START, "summarizer")
    .add_edge('summarizer', "combiner")
    .add_edge("combiner", END)
)
