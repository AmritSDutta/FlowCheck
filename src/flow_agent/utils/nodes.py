import logging

from google.genai import types
from google.genai.chats import AsyncChat
from google.genai.types import GenerateContentResponse
from langchain_core.messages import AIMessage, BaseMessage, convert_to_messages, get_buffer_string
from langgraph.constants import END
from langgraph.runtime import Runtime
from langgraph.types import Command
from langgraph_api.schema import Context

from src.flow_agent.llms.genai_classifier_agent import get_combiner_agent
from src.flow_agent.utils.state import State


async def call_combiner_model(state: State, runtime: Runtime[Context]) -> Command:
    user_message: list[BaseMessage] = state.get("messages")
    ctm = convert_to_messages(user_message)
    gbt = get_buffer_string(ctm, human_prefix="", ai_prefix="").strip()
    logging.info(gbt)
    if not user_message:
        logging.info(user_message)
        return Command(update={"retry_count": state["retry_count"], "messages": state["messages"]}, goto=END)

    agent: AsyncChat = await get_combiner_agent()
    logging.info(f'user requirement: {gbt}')
    response = await agent.send_message(gbt)
    genai_res: AIMessage | None = AIMessage('did nto get it, please re ask.')
    if response and response.text:
        logging.info(f'Agent response: {response.text}')
        logging.info(f'Agent token usage: {response.usage_metadata.total_token_count}')
        genai_res = AIMessage(response.text)

    return Command(update={
        "retry_count": state["retry_count"],
        "messages": genai_res
    }, goto=END)
