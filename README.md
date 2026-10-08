# FlowCheck

> Parallel incident evaluation and decision automation using **LangGraph** with an **orchestrator–worker fan-out/fan-in architecture**.

FlowCheck ingests unstructured incident alerts, logs, and issue descriptions, summarizes the incident context using **Google Gemini**, evaluates independent operational actions in parallel using **OpenAI Agents**, and deterministically aggregates outcomes into a structured, unified action plan.

---

## ⚡ Architectural Overview

```
START
  ↓
entry (thread guard: ended_once check)
  ↓
summarizer (Gemini 2.5 Flash Lite)
  ↓
assign_workers (conditional edge: fan-out)
  ├─ Send → subtask (reset_vpn_profile)
  ├─ Send → subtask (restart_sso_session)
  ├─ Send → subtask (run_connectivity_diagnostics)
  ├─ Send → subtask (update_internal_record)
  ├─ Send → subtask (send_notification)
  └─ Send → subtask (approval_required)
  ↓ (automatic list concatenation via operator.add)
combiner (deterministic plan assembly)
  ↓
END
```

### Components

| Component | Node / Edge | Model / Technology | Responsibility |
| :--- | :--- | :--- | :--- |
| **Thread Guard** | `entry` / `should_continue` | Python Logic | Prevents re-entry on previously completed threads. |
| **Summarizer** | `summarizer` | **gemini-2.5-flash-lite** | Distills raw incident text into a structured issue summary. |
| **Fan-Out Orchestrator** | `assign_workers` | Conditional Edge | Dispatches parallel `Send("subtask", ...)` payload branches. |
| **Subtask Evaluators** | `subtask` | **gpt-5-nano** | Evaluates individual decision viability with dynamic instructions. |
| **Fan-In Combiner** | `combiner` | Python Logic (Pydantic) | Deterministically merges evaluator outputs into `CombinedPlan`. |

---

## 📋 Decision Catalog

FlowCheck currently evaluates six specialized operational actions:

| Decision ID | Trigger Condition |
| :--- | :--- |
| `reset_vpn_profile` | Repeated VPN disconnects, corrupted tunnel profiles, or gateway auth errors. |
| `restart_sso_session` | Expired tokens, SAML/OAuth session loops, or authentication rejections. |
| `run_connectivity_diagnostics` | Network dropouts, unreachable microservices, or packet loss indications. |
| `update_internal_record` | Status updates, onboarding/offboarding events, or CMDB asset drift. |
| `send_notification` | Escalation alerts, stakeholder communications, or paging on-call staff. |
| `approval_required` | Compliance policies, elevated production access, or exception approvals. |

---

## 📊 State Schema

```python
class State(TypedDict):
    retry_count: Annotated[int, operator.add]
    messages: Annotated[list[BaseMessage], add_messages]
    issue: str
    sub_issues_decision: tuple[str, ...]
    sub_issue: NotRequired[str]
    completed_sub_issues_decision: Annotated[list, operator.add]
    final_report: CombinedPlan
    ended_once: bool
```

### Reducer Guarantees
- `completed_sub_issues_decision` uses `operator.add` to automatically concatenate parallel worker outputs.
- `sub_issue` is dynamically injected into each worker's isolated payload via `Send()`.
- Deterministic assembly ensures decisions with `confidence >= 0.6` trigger their respective plan actions.

---

## 🚀 Quickstart

### Prerequisites
- Python 3.10+
- Node.js 20.19+ (for documentation preview)
- API Keys for Google Gemini and OpenAI

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/amrit/FlowCheck.git
cd FlowCheck

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install package dependencies
pip install -e ".[dev]"
pip install streamlit requests
```

### 2. Environment Variables

Set your provider credentials:

```bash
export GEMINI_API_KEY="your-gemini-key"
export OPENAI_API_KEY="your-openai-key"
```

### 3. Running the Server

Start the LangGraph development server:

```bash
langgraph dev
```

The API service starts at `http://localhost:2024`.

### 4. Running the Streamlit UI

In a separate terminal:

```bash
python -m streamlit run ui/app.py
```

Open `http://localhost:8501` to paste incident logs and execute runs.

### 5. Running Tests

```bash
pytest tests/unit_tests/test_combiner.py
```

---

## 📖 Documentation

Full project documentation is powered by **docs7** in the `docs/` folder:

```bash
# Preview docs locally
npx docs7 dev docs --port 3333
```

Navigate to `http://localhost:3333` to browse:
- **System Architecture**: Detailed state graph transitions and fan-out/fan-in lifecycle.
- **Decision Evaluators**: Trigger conditions and dynamic prompt contracts.
- **Data Models**: Pydantic schema specifications and reducer semantics.
- **UI & Deployment**: Streamlit client details and server operations.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
