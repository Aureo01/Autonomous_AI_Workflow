# Emiglio — AI Workflow Automation Agent

Emiglio is a conversational AI assistant built on LangGraph and Claude that executes **chained, multi-step workflows** from a single natural language instruction. It can summarize, draft emails, translate, generate reports, run code, search the web, and manage files — all in sequence, passing results between steps automatically.

---

## Features

- **Multi-step chaining** — issue compound instructions like *"summarize this + extract key points + save to file"* and Emiglio handles the full pipeline
- **Self-calling AI tools** — several tools invoke the Anthropic API internally (summarization, drafting, translation, etc.)
- **Persistent workspace** — all files are saved to `emiglio_workspace/` and can be listed, read, or reused across turns
- **Conversation memory** — pass `history` to maintain context across multiple interactions
- **Step logging** — every tool call is logged with timestamp, tool name, and a result preview

---

## Requirements

- Python 3.9+
- An [Anthropic API key](https://console.anthropic.com/)
- A [Tavily API key](https://tavily.com/) *(only required for `search_web`)*

---

## Getting started

**1. Clone the repo**
```bash
git clone https://github.com/Aureo01/Autonomous_AI_Workflow.git
cd Autonomous_AI_Workflow
```

**2. Install dependencies**
```bash
pip install langgraph langchain langchain-openai numpy torch
```

**3. Set your OpenAI API key**
```bash
export OPENAI_API_KEY=your-key-here
```

**4. Run**
```bash
python nexuscore_factory.py
```

You'll see the CLI dashboard start up. Press Enter to trigger a reasoning cycle, type `/exit` to shut down.

---

## Installation

```bash
pip install anthropic langchain-anthropic langchain-community langgraph
```

Set your API keys either via environment variables or directly in the script:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export TAVILY_API_KEY="tvly-..."
```

---

## Quick Start

```python
from emiglio import run_workflow

result = run_workflow("Hello Emiglio, what can you do?")
print(result["response"])
```

**Multi-step example:**

```python
result = run_workflow(
    "Summarize this text + extract 3 key points + save it as 'ai_summary':\n"
    "Artificial intelligence has transformed multiple industries..."
)

print(result["response"])   # Emiglio's final reply
print(result["steps"])      # List of tool calls with timestamps
print(result["files"])      # Files currently in the workspace
```

---

## Available Tools

| Tool | Description |
|---|---|
| `summarize_text` | Summarizes text in four styles: `concise`, `detailed`, `bullet_points`, `executive` |
| `draft_email` | Drafts a complete email given subject, context, tone, recipient, and sender |
| `save_file` | Saves content to the workspace; supports `txt`, `md`, `json`, `html`, `csv`, `py` |
| `read_file` | Reads a file from the workspace by name (partial matches supported) |
| `list_files` | Lists all files in the workspace with size and modification date |
| `extract_key_points` | Extracts N key points (1–10) from a given text |
| `translate_text` | Translates text into any language while preserving formatting |
| `create_report` | Generates a structured Markdown report from a title and comma-separated section names |
| `run_python_code` | Executes sandboxed Python (math, strings, lists) — no system/network access |
| `search_web` | Searches the internet for up-to-date information via Tavily |

---

## `run_workflow` API

```python
run_workflow(
    user_message: str,
    history: list[dict] | None = None,
    on_step: Callable | None = None,
) -> dict
```

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `user_message` | `str` | The instruction to execute (can be multi-step) |
| `history` | `list[dict]` | Optional prior conversation `[{"role": "user"/"assistant", "content": "..."}]` |
| `on_step` | `Callable` | Optional callback fired after each tool step (useful for streaming UIs) |

**Returns**

```python
{
    "response": str,   # Emiglio's final text reply
    "steps": [         # List of executed tool calls
        {
            "timestamp":   "14:32:01",
            "tool":        "summarize_text",
            "description": "Summary style 'concise'",
            "preview":     "AI has transformed..."
        },
        ...
    ],
    "files": ["summary_demo.txt", "email_delay.md", ...]  # Workspace contents
}
```

---

## Chaining Instructions

Emiglio recognizes compound instructions joined by `+`, `then`, `after`, or `and also`. Results flow automatically from one step to the next.

```
"Summarize this article + translate the summary to French + save it as 'french_summary'"

"Search for the latest AI news + create a report with the findings + save it as 'ai_news_report'"

"Draft a professional email about the project delay + translate it to Spanish + save both versions"
```

---

## Architecture

Emiglio is built as a **LangGraph ReAct agent**:

```
User message
     │
     ▼
 agent_node  ──(tool calls?)──▶  tools_node
     ▲                                │
     └────────────────────────────────┘
     │
     ▼ (no tool calls)
 Final response
```

- `agent_node` — runs `claude-opus-4-5` with all tools bound via `bind_tools`
- `tools_node` — executes every tool call in the last agent message
- `should_continue` — routes back to agent if tool calls were made, otherwise ends

The graph loops until the model produces a message with no tool calls.

---

## Workspace

All files created by `save_file` are stored in `emiglio_workspace/` relative to where the script runs. The directory is created automatically on first run.

```
emiglio_workspace/
├── summary_demo.txt
├── email_delay.md
└── ai_news_report.md
```

Use `list_files` or check `result["files"]` to see current contents.

---

## Security Notes

`run_python_code` blocks the following to prevent unsafe execution:

- `import os`, `import sys`, `import subprocess`
- `open(`, `exec(`, `eval(`
- `requests`, `urllib`, `socket`
- `__import__`

Code is also run in a subprocess with a **5-second timeout**.

---

## Running the Demo

The script includes three built-in demo tasks:

```bash
Emiglio_agent_v4.py
```

This will run:
1. A greeting / capability overview
2. A summarize → extract key points → save workflow
3. A draft email → save → translate workflow

---

## License

MIT
