# FlowCheck Agent Specifications & Contributor Guidelines

This document provides a detailed specification of the agents operating within the FlowCheck pipeline, as well as operational guidelines for AI coding assistants working on this codebase.

---

## 🤖 Pipeline Agents Specification

FlowCheck coordinates multiple specialized agents via LangGraph's state machine.

### 1. Global Summarizer Agent

- **Implementation**: [`get_summarizer_agent()`](file:///C:/Users/amrit/github_codes/FlowCheck/src/flow_agent/llms/genai_agent.py)
- **Model**: `gemini-2.5-flash-lite`
- **Framework**: Google GenAI SDK (`google.genai.chats.AsyncChat`)
- **System Instruction**:
  - Distills unstructured text into an issue summary preserving events, dates, and numbers.
  - Prioritizes issues over user context.
  - Compresses emotional phrasing, greetings, and lengthy prose.
- **Safety Settings**: Configured across Hate Speech, Dangerous Content, Harassment, Sexually Explicit, and Civic Integrity.
- **Input**: Raw buffer string parsed from input messages.
- **Output**: Summary string stored in `state["issue"]`.

### 2. Subtask Evaluator Agents

- **Implementation**: [`get_sub_task_agent_instance()`](file:///C:/Users/amrit/github_codes/FlowCheck/src/flow_agent/llms/sub_task_agent.py)
- **Model**: `gpt-5-nano`
- **Framework**: OpenAI Agents SDK (`agents.Agent`, executed via `agents.Runner.run`)
- **Target Schema**: [`DecisionOutput`](file:///C:/Users/amrit/github_codes/FlowCheck/src/flow_agent/data_objs/business_objs.py)
- **Context Injection**: Uses `DecisionContext(decision_id, context)` passed to dynamic instruction generator.
- **Dynamic Instructions**: Synthesizes custom evaluation tasks per `decision_id` referencing criteria in `DECISION_TRIGGERS`.
- **JSON Output Contract**:
  ```json
  {
    "decision_id": "<decision_id>",
    "decision": true,
    "confidence": 0.0,
    "model": "gpt-5-nano",
    "notes": "concise rationale (max 10 words)",
    "latency_ms": null
  }
  ```

---

## 📐 Graph & Reducer Invariants

When extending or modifying agent definitions in this repository, preserve these invariants:

1. **Fan-Out via `Send()`**: The fan-out edge `assign_workers` must return `[Send("subtask", payload)]`. Fan-out logic must **never** be registered as a standard graph node.
2. **Worker Return Contract**: Each worker must return a dictionary updating `completed_sub_issues_decision` as a **list** (e.g., `{"completed_sub_issues_decision": [result.final_output]}`).
3. **List Concatenation**: In `State`, `completed_sub_issues_decision` must use `Annotated[list, operator.add]` to guarantee deterministic list combination.
4. **Isolated Branch Payloads**: Workers must only receive the context required for their specific evaluation task (`sub_issue`).
5. **Thread Idempotency**: The `entry` node checks `state.get("ended_once")`. Closed threads must terminate immediately at `END`.

---

## 🛠️ Contributor Guidelines for AI Coding Assistants

When contributing or assisting on this repository, all AI agents must adhere to the following rules:

### 1. Security & Confidentiality
- **Never access `.env*` files**: Do not inspect, read, or print any file matching `.env*`.
- **No environment variable inspection**: Do not dump system or user environment variables.

### 2. Git & Version Control
- **User commits only**: AI assistants must never run `git commit`, `git push`, or `git stash`.
- **No destructive operations**: Do not use `git reset --hard`, `git checkout .`, or `git clean -f`.
- **Read-only inspection**: Only `git status` or read-only `git diff` / `git log` is permitted.

### 3. Code Standards & Typing
- **Strict Type Hints**: All Python functions, methods, parameters, and return types must include explicit type annotations.
- **High-Signal Docstrings**: Write short, 1–2 line docstrings summarizing purpose. Avoid verbose boilerplate.
- **Minimal Comments**: Only comment non-obvious logic or critical invariants.
- **PEP 8**: Follow standard Python conventions, formatted with Ruff.

### 4. Verification
- Validate changes by running unit tests (`pytest tests/unit_tests/test_combiner.py`).
- If documentation is modified, validate with `node ~/.gemini/config/skills/docs7/scripts/validate_docs7.mjs docs`.
