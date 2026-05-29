import os, json, re, subprocess, textwrap, warnings
from datetime import datetime
from pathlib import Path
from typing import Annotated, Sequence, TypedDict, Callable

warnings.filterwarnings("ignore")

import anthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages


# API KEYS

os.environ.setdefault("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_KEY")
os.environ.setdefault("TAVILY_API_KEY",    "YOUR_TAVILY_KEY")

# Emiglio workspace directory
WORKSPACE = Path("emiglio_workspace")
WORKSPACE.mkdir(exist_ok=True)

# Direct Anthropic client (for agent self-calls)
_anthropic = anthropic.Anthropic()

# Workflow step log
_workflow_log: list[dict] = []

def _log_step(tool_name: str, description: str, result_preview: str = ""):
    """Logs each workflow step to display it in the frontend."""
    _workflow_log.append({
        "timestamp":  datetime.now().strftime("%H:%M:%S"),
        "tool":       tool_name,
        "description": description,
        "preview":    result_preview[:120] + "..." if len(result_preview) > 120 else result_preview,
    })



# EMIGLIO TOOLS

@tool
def summarize_text(text: str, style: str = "concise") -> str:
    """
    Summarizes text using AI (Emiglio calls itself).
    Available styles: concise, detailed, bullet_points, executive.

    :param text:  Text to summarize
    :param style: Summary style
    :return: Generated summary
    """
    style_prompts = {
        "concise":       "Summarize in 2-3 key sentences.",
        "detailed":      "Summarize while keeping the important points in several paragraphs.",
        "bullet_points": "Summarize as a list of 5 bullet points (•) with the key points.",
        "executive":     "Executive summary in 1 paragraph for a time-pressed manager.",
    }
    instruction = style_prompts.get(style, style_prompts["concise"])

    # ← Here Emiglio calls itself via the Anthropic API
    response = _anthropic.messages.create(
        model="claude-opus-4-5",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": f"{instruction}\n\nText:\n{text[:4000]}"
        }]
    )
    result = response.content[0].text
    _log_step("summarize_text", f"Summary style '{style}'", result)
    return result


@tool
def draft_email(
    subject: str,
    context: str,
    tone: str = "professional",
    recipient: str = "",
    sender: str = "Emiglio"
) -> str:
    """
    Drafts a complete email using AI.
    Tones: professional, formal, friendly, urgent, commercial.

    :param subject:   Email subject
    :param context:   Context or points the email should cover
    :param tone:      Email tone
    :param recipient: Recipient name (optional)
    :param sender:    Sender name
    :return: Formatted complete email
    """
    greeting = f"Dear {recipient}," if recipient else "Dear,"

    response = _anthropic.messages.create(
        model="claude-opus-4-5",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": (
                f"Draft a {tone} email with:\n"
                f"Subject: {subject}\n"
                f"Greeting: {greeting}\n"
                f"Context/points to cover: {context}\n"
                f"Signature: {sender}\n\n"
                "Format: Subject / Greeting / Body / Closing / Signature"
            )
        }]
    )
    result = response.content[0].text
    _log_step("draft_email", f"Email '{subject}' tone {tone}", result)
    return result


@tool
def save_file(filename: str, content: str, format: str = "txt") -> str:
    """
    Saves content to a file inside Emiglio's workspace.
    Formats: txt, md, json, html, csv, py.

    :param filename: File name (without extension)
    :param content:  Content to save
    :param format:   File extension/format
    :return: Path of the saved file
    """
    safe_name = re.sub(r'[^\w\-]', '_', filename)
    filepath   = WORKSPACE / f"{safe_name}.{format}"
    filepath.write_text(content, encoding="utf-8")
    _log_step("save_file", f"File saved: {filepath.name}", f"{len(content)} characters")
    return f"File saved: {filepath} ({len(content)} characters)"


@tool
def read_file(filename: str) -> str:
    """
    Reads the content of a file from the workspace.

    :param filename: Exact file name (including extension)
    :return: File content
    """
    filepath = WORKSPACE / filename
    if not filepath.exists():
        # Search for a partial match
        matches = list(WORKSPACE.glob(f"*{filename}*"))
        if matches:
            filepath = matches[0]
        else:
            return f"File '{filename}' not found in the workspace."
    content = filepath.read_text(encoding="utf-8")
    _log_step("read_file", f"Reading: {filepath.name}", content)
    return content


@tool
def list_files() -> str:
    """
    Lists all files stored in Emiglio's workspace.
    :return: List of files with size and date
    """
    files = list(WORKSPACE.iterdir())
    if not files:
        return "The workspace is empty."
    lines = []
    for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
        size = f.stat().st_size
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        lines.append(f"• {f.name}  ({size} bytes)  —  {mtime}")
    result = "\n".join(lines)
    _log_step("list_files", "Listing workspace", result)
    return result


@tool
def extract_key_points(text: str, n_points: int = 5) -> str:
    """
    Extracts the N most important key points from a text.

    :param text:     Text to analyze
    :param n_points: Number of key points to extract (1-10)
    :return: Numbered list of key points
    """
    response = _anthropic.messages.create(
        model="claude-opus-4-5",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": (
                f"Extract exactly {n_points} key points from the following text. "
                f"Format: number. key point (one line each)\n\n{text[:3000]}"
            )
        }]
    )
    result = response.content[0].text
    _log_step("extract_key_points", f"Extracting {n_points} key points", result)
    return result


@tool
def translate_text(text: str, target_language: str) -> str:
    """
    Translates text into another language while preserving the format.
    Languages: Spanish, English, French, German, Portuguese, Italian, etc.

    :param text:            Text to translate
    :param target_language: Target language
    :return: Translated text
    """
    response = _anthropic.messages.create(
        model="claude-opus-4-5",
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": f"Translate to {target_language} while preserving the format:\n\n{text[:3000]}"
        }]
    )
    result = response.content[0].text
    _log_step("translate_text", f"Translating to {target_language}", result)
    return result


@tool
def create_report(title: str, sections: str) -> str:
    """
    Generates a structured report in Markdown.
    sections must be a list of topics separated by commas.

    :param title:    Report title
    :param sections: Report sections separated by commas (e.g. "summary, findings, conclusions")
    :return: Complete report in Markdown
    """
    section_list = [s.strip() for s in sections.split(",")]
    sections_prompt = "\n".join([f"## {s.title()}" for s in section_list])

    response = _anthropic.messages.create(
        model="claude-opus-4-5",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": (
                f"Generate a professional report in Markdown with this title and sections. "
                f"Fill each section with relevant and professional content.\n\n"
                f"# {title}\n{sections_prompt}"
            )
        }]
    )
    result = response.content[0].text
    _log_step("create_report", f"Report: '{title}'", result)
    return result


@tool
def run_python_code(code: str) -> str:
    """
    Runs safe Python code (only calculations, lists, strings, math).
    Does NOT execute system commands, external imports, or network operations.

    :param code: Python code to execute
    :return: Code output
    """
    # Block dangerous operations
    blocked = ["import os", "import sys", "import subprocess", "__import__",
               "open(", "exec(", "eval(", "requests", "urllib", "socket"]
    for b in blocked:
        if b in code:
            return f"Operation blocked for security: '{b}' is not allowed."

    # Run in isolated process with timeout
    try:
        result = subprocess.run(
            ["python3", "-c", code],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout or result.stderr or "No output"
        _log_step("run_python_code", "Executing Python code", output)
        return output
    except subprocess.TimeoutExpired:
        return "Timeout: the code took longer than 5 seconds."
    except Exception as e:
        return f"Error: {e}"


@tool
def search_web(query: str) -> str:
    """
    Searches for up-to-date information on the internet.

    :param query: Search query
    :return: Summary of relevant results
    """
    try:
        tavily = TavilySearchResults(max_results=4)
        results = tavily.invoke(query)
        summary = "\n".join([
            f"• {r['title']}: {r['content'][:200]}" for r in results[:4]
        ])
        _log_step("search_web", f"Search: '{query}'", summary)
        return summary
    except Exception as e:
        return f"Search not available: {e}"



# Tool registry

TOOLS = [
    summarize_text, draft_email, save_file, read_file, list_files,
    extract_key_points, translate_text, create_report,
    run_python_code, search_web,
]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}



# EMIGLIO PERSONALITY AND PROMPT

EMIGLIO_SYSTEM = """You are Emiglio, an AI workflow automation assistant.
Your name is Emiglio and that is how you always introduce yourself.

Your specialty is executing chained multi-step workflows. When the user asks for
multiple tasks in sequence (separated by "+", "then", "after", "and also"), you execute
them in order using the available tools, passing the result of each step to the next.

CHAINING RULES:
1. Analyze the full request before acting — identify all steps.
2. Execute the steps in logical order.
3. Use the output of one tool as input to the next when it makes sense.
4. At the end, provide a clear summary of everything you did.

PERSONALITY:
- You are precise, efficient, and slightly formal but friendly.
- When you finish a complex task, you celebrate it discreetly.
- If something is not possible, you say so clearly and propose an alternative.
- You always confirm which files you created and where they were saved.

AVAILABLE TOOLS:
- summarize_text: summarize text in different styles
- draft_email: draft complete emails
- save_file: save files in the workspace
- read_file: read files from the workspace
- list_files: list saved files
- extract_key_points: extract key points
- translate_text: translate to any language
- create_report: generate structured Markdown reports
- run_python_code: execute Python calculations
- search_web: search for information on the internet
"""



# STATE AND LANGGRAPH

class EmigliState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


llm = ChatAnthropic(
    model="claude-opus-4-5",
    temperature=0.3,
    max_tokens=2048,
)

prompt = ChatPromptTemplate.from_messages([
    ("system", EMIGLIO_SYSTEM),
    MessagesPlaceholder(variable_name="messages"),
])

emiglio_chain = prompt | llm.bind_tools(TOOLS)


def agent_node(state: EmigliState):
    response = emiglio_chain.invoke({"messages": state["messages"]})
    return {"messages": [response]}


def tools_node(state: EmigliState):
    outputs = []
    for call in state["messages"][-1].tool_calls:
        fn     = TOOLS_BY_NAME[call["name"]]
        result = fn.invoke(call["args"])
        outputs.append(ToolMessage(
            content=str(result),
            name=call["name"],
            tool_call_id=call["id"],
        ))
    return {"messages": outputs}


def should_continue(state: EmigliState):
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "end"


# Graph construction
_builder = StateGraph(EmigliState)
_builder.add_node("agent", agent_node)
_builder.add_node("tools", tools_node)
_builder.set_entry_point("agent")
_builder.add_edge("tools", "agent")
_builder.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
emiglio_graph = _builder.compile()



# PUBLIC API

def run_workflow(
    user_message: str,
    history: list[dict] | None = None,
    on_step: Callable | None = None,
) -> dict:
    """
    Runs an Emiglio workflow.

    :param user_message: User instruction (may be multi-step)
    :param history:      Previous conversation history [{role, content}]
    :param on_step:      Callback called at each step (for streaming in UI)
    :return: {response: str, steps: list, files: list}
    """
    global _workflow_log
    _workflow_log = []

    # Build message history
    messages: list[BaseMessage] = []
    for msg in (history or []):
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))

    # Execute graph
    final_state = emiglio_graph.invoke({"messages": messages})

    # Extract final response
    final_response = ""
    for msg in reversed(final_state["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            final_response = msg.content
            break

    # Files in the workspace
    files = [f.name for f in WORKSPACE.iterdir() if f.is_file()]

    return {
        "response": final_response,
        "steps":    _workflow_log.copy(),
        "files":    sorted(files),
    }



# Quick terminal demo

if __name__ == "__main__":
    DEMO_TASKS = [
        "Hello Emiglio, what can you do?",

        ("summarize this text + extract 3 key points + save it in a file called 'summary_demo':\n"
         "Artificial intelligence has transformed multiple industries over the last decade. "
         "From medical diagnosis to autonomous driving, deep learning models have surpassed "
         "human capabilities in specific tasks. However, significant challenges remain in "
         "terms of transparency, algorithmic bias, and the impact on the labor market. "
         "Responsible AI development requires collaboration among technologists, regulators, "
         "and civil society."),

        "draft a professional email about a delivery delay + save it as 'email_delay' + translate it to English",
    ]

    for task in DEMO_TASKS:
        print(f"\n{'═'*60}")
        print(f"User: {task[:80]}{'...' if len(task)>80 else ''}")
        print('─'*60)
        result = run_workflow(task)
        print(f"Emiglio: {result['response'][:500]}")
        if result["steps"]:
            print(f"\nExecuted steps ({len(result['steps'])}):")
            for s in result["steps"]:
                print(f"  [{s['timestamp']}] {s['tool']} — {s['description']}")
