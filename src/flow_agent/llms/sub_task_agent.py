from asyncio import Lock

from agents import Agent, RunContextWrapper, ModelSettings

from src.flow_agent.data_objs.business_objs import DecisionContext, DecisionOutput, DECISION_TRIGGERS, CombinedPlan

_combiner_agent_instance = None
_auditor_agent_instance = None

_lock = Lock()


def dynamic_instructions(
        context: RunContextWrapper[DecisionContext], agent: Agent[DecisionContext]
) -> str:
    return f"""
    as a agent of {context.context.decision_id}. 
    You are an automated decision evaluator.

    Input:
    - decision_id: {context.context.decision_id}
    - context: unstructured text containing events, logs, symptoms, actions, or user reports.
    
    Task:
    1. Read and interpret the context.
    2. Based solely on the meaning of the decision_id, determine if action is required:
       - {DECISION_TRIGGERS.get(context.context.decision_id)}
    3. Return:
       - decision: true if action is warranted, false otherwise
       - confidence: 0.0–1.0 expressing certainty
       - model: name of the model producing the output
       - notes: concise reasoning (optional)
       - latency_ms: leave empty
    
    Output JSON strictly in the following structure:
    
    {
    "decision_id": "<same as input>",
      "decision": <true|false>,
      "confidence": <0.0–1.0>,
      "model": "<model name>",
      "notes": "<short rationale>",
      "latency_ms": null
    }

    Help them with their questions.
    """


sub_task_agent = Agent[DecisionContext](
    model='gpt-5-nano',
    name="Issue_evaluator",
    instructions=dynamic_instructions,
    output_type=DecisionOutput
)

_combiner_prompt = """
You are a useful assistant.
"""


async def get_combiner_agent():
    global _combiner_agent_instance
    if _combiner_agent_instance is None:
        with _lock:
            if _combiner_agent_instance is None:  # double-checked lock
                _combiner_agent_instance = Agent(
                    model='gpt-5-mini',
                    name="combiner_agent",
                    instructions=_combiner_prompt,
                    output_type=CombinedPlan,
                    model_settings=ModelSettings()
                )
    return _combiner_agent_instance
