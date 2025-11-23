import logging
from typing import get_args

from agents import Runner
from google.genai.chats import AsyncChat
from langchain_core.messages import AIMessage, BaseMessage, convert_to_messages, get_buffer_string
from langgraph.constants import END
from langgraph.runtime import Runtime
from langgraph.types import Command, Send
from langgraph_api.schema import Context

from src.flow_agent.data_objs.business_objs import DecisionOutput, CombinedPlan, DecisionID, DecisionContext
from src.flow_agent.llms.genai_agent import get_summarizer_agent
from src.flow_agent.llms.sub_task_agent import get_sub_task_agent_instance
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
        "messages": genai_res,
        'sub_issues_decision':  get_args(DecisionID),
        'completed_sub_issues_decision': [],
    }, goto='combiner')


async def call_combiner_model(state: State, runtime: Runtime[Context]) -> Command:
    issue_summary: str = state['issue']
    decisions: list[DecisionOutput] = state['completed_sub_issues_decision']
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


async def call_subtask_model(state: State, runtime: Runtime[Context]):
    """Worker writes a section of the report"""

    """
       Worker: evaluate a single decision_id and append DecisionOutput.
       Expects state["decision_id"] injected via Send().
       """

    sub_issue: str = state["sub_issue"]
    logging.info(f'executing {sub_issue}')

    agent = await get_sub_task_agent_instance()
    decision_ctx = DecisionContext(
        context=state["issue"],
        decision_id=sub_issue,
        # add any other DecisionContext fields you have
    )
    result = await Runner.run(
        starting_agent=agent,
        input=f"Evaluate decision_id={sub_issue} for issue: {state['issue']}",
        context=decision_ctx,
    )
    output_dump = result.final_output.model_dump_json(indent=2)
    logging.info(f'post execution- {sub_issue}, decision : {output_dump}')
    return {
        "completed_sub_issues_decision": [result.final_output]
    }


async def assign_workers(state: State, runtime: Runtime[Context]):
    """Assign a worker to each section in the plan"""
    sub_issues = state["sub_issues_decision"]

    if not sub_issues:
        # no work → skip directly to combiner
        return "combiner"

    return [
        Send("subtask", {**state, "sub_issue": s})
        for s in sub_issues
    ]
