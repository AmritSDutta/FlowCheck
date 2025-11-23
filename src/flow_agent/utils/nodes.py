import logging

from google.genai.chats import AsyncChat
from langchain_core.messages import AIMessage, BaseMessage, convert_to_messages, get_buffer_string
from langgraph.constants import END
from langgraph.runtime import Runtime
from langgraph.types import Command
from langgraph_api.schema import Context

from src.flow_agent.data_objs.business_objs import DecisionOutput, CombinedPlan
from src.flow_agent.llms.genai_classifier_agent import get_combiner_agent, get_summarizer_agent
from src.flow_agent.utils.state import State


async def call_summarizer_model(state: State, runtime: Runtime[Context]) -> Command:
    user_message: list[BaseMessage] = state.get("messages")
    ctm = convert_to_messages(user_message)
    gbt = get_buffer_string(ctm, human_prefix="", ai_prefix="").strip()
    logging.info(gbt)
    if not user_message:
        logging.info(user_message)
        return Command(update={"retry_count": state["retry_count"], "messages": state["messages"]}, goto=END)

    agent: AsyncChat = await get_summarizer_agent()
    logging.info(f'user requirement: {gbt}')
    response = await agent.send_message(gbt)
    summary: str | None = 'not available'
    genai_res: AIMessage | None = AIMessage('did nto get it, please re ask.')
    if response and response.text:
        logging.info(f'Agent summarization response: {response.text}')
        logging.info(f'Agent token usage: {response.usage_metadata.total_token_count}')
        genai_res = AIMessage(response.text)
        summary = response.text

    return Command(update={
        "issue": summary,
        'sub_issues_decision': [],
        "messages": genai_res
    }, goto='combiner')


async def call_combiner_model(state: State, runtime: Runtime[Context]) -> Command:
    issue_summary: str = state['issue']
    decisions: list[DecisionOutput] = state['sub_issues_decision']
    final_output: CombinedPlan = (CombinedPlan
                                  .assemble_from_evaluators(decisions,
                                                            additional_summary=issue_summary if issue_summary else ''))
    logging.info(final_output)

    if not final_output:
        return Command(update={"messages": state["messages"]}, goto=END)

    output_dump = final_output.model_dump_json(indent=2)
    logging.info(output_dump)

    return Command(update={
        "final_report": final_output,
        "messages": AIMessage(output_dump)
    }, goto=END)


"""

result = await Runner.run(agent, "What city is the Golden Gate Bridge in?", session=session)
        print(result.final_output)
        
        
async def call_combiner_model(state: State, runtime: Runtime[Context]) -> Command:
    user_message: list[BaseMessage] = state.get("messages")
    ctm = convert_to_messages(user_message)
    gbt = get_buffer_string(ctm, human_prefix="", ai_prefix="").strip()
    logging.info(gbt)
    if not user_message:
        logging.info(user_message)
        return Command(update={"retry_count": state["retry_count"], "messages": state["messages"]}, goto=END)

    issue: str = state['issue']
    agent: AsyncChat = await get_combiner_agent()
    logging.info(f'user issue: {issue}')
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
"""
