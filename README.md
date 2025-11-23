# FlowCheck

# Using Orchestrator–Worker Architecture

## Overview

FlowCheck implements a parallel evaluation pipeline for decision automation using **LangGraph** with an **orchestrator–worker fan‑out/fan‑in pattern**. The system:

1. Extracts and summarizes input context
2. Dispatches parallel decision evaluators
3. Aggregates all outputs into a unified final report

This design enables scalable execution while ensuring deterministic aggregation of results.

---

## Architectural Components

### ✅ Summarizer (Global Context Builder)

* Node: `summarizer`
* Model: **gpt‑2.5‑flash‑lite**
* Responsibilities:

  * interpret raw issue input
  * generate structured `issue`
  * produce `sub_issues_decision: list[DecisionOutput]`

### ✅ Fan‑Out Executor (Orchestrator)

* Implemented as **conditional edge**, not a node
* Function: `assign_workers`
* Generates:

  ```python
  [Send("subtask", payload) ...]
  ```
* Each dispatched branch receives isolated `sub_issue`

### ✅ Worker Nodes (Parallel Evaluation)

* Node: `subtask`
* Model: **gpt‑5‑nano**
* Execution via:

  ```python
  Runner.run(starting_agent, input, context)
  ```
* Returns:

  ```python
  {"completed_sub_issues_decision": [DecisionOutput]}
  ```

### ✅ Fan‑In Aggregator

* Node: `combiner`
* Input merged automatically because:

  ```python
  completed_sub_issues_decision: Annotated[list[DecisionOutput], operator.add]
  ```
* Produces:

  ```python
  final_report: CombinedPlan
  ```

---

## State Definition

```python
class State(TypedDict):
    retry_count: Annotated[int, add]
    messages: Annotated[list[BaseMessage], add_messages]
    issue: str
    sub_issues_decision: list[DecisionOutput]
    sub_issue: NotRequired[DecisionOutput]
    completed_sub_issues_decision: Annotated[list[DecisionOutput], operator.add]
    final_report: CombinedPlan
```

### Why this matters

* `operator.add` enables list concatenation during fan‑in
* `sub_issue` is optional because it only exists inside worker branches
* messages and retry_count remain compatible with LangGraph execution

---

## Execution Flow

```
START
  ↓
summarizer
  ↓
assign_workers  (conditional edge)
  ├─ Send → subtask (worker 1)
  ├─ Send → subtask (worker 2)
  ├─ Send → subtask (worker 3)
  …
  ↓ (after all workers complete)
combiner
  ↓
END
```

---

## Key Rules and Guarantees

✅ Fan‑out must return Send(), not dict
✅ Fan‑out must not be registered as a node
✅ Worker return values must be dicts
✅ Worker outputs must be lists
✅ Shared state must be passed into Send payload
✅ Dynamic instructions must escape braces if using f‑strings
✅ Null fields like `notes` must be normalized

---

## Model Selection Rationale

| Component       | Model                  | Reason                               |
| --------------- | ---------------------- | ------------------------------------ |
| summarizer      | **gpt‑2.5‑flash‑lite** | inexpensive global contextualization |
| subtask workers | **gpt‑5‑nano**         | fast, structured, parallelizable     |
| final combiner  | inherits context       | purely deterministic merging         |

This yields cost‑efficient scaling because heavy reasoning doesn’t run per worker.

---

## Suggested Enhancements

✅ concurrency limiter (e.g., max 3 workers)
✅ telemetry: latency, decision rate, disagreement counts
✅ cost attribution per decision_id
✅ retry policy only at worker level

---

## When to Use This Architecture

Use it if you need:
✅ independent evaluations per decision type
✅ consistent aggregation
✅ heterogeneous model assignment
✅ parallelism with deterministic merge semantics

Do **not** use if:
❌ decisions depend on each other
❌ ordering impacts evaluation

---

## License

Internal architectural documentation for FlowCheck.
