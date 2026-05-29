import streamlit as st
from pathlib import Path
from datetime import datetime

# Import the agent
from emiglio_agent import run_workflow, WORKSPACE


# PAGE CONFIGURATION
st.set_page_config(
    page_title="Emiglio — AI Workflow Assistant",
    page_icon="Emiglio.v4",
    layout="wide",
    initial_sidebar_state="expanded",
)


# CSS — Retro-futuristic aesthetic: terminal green on black
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    background-color: #080e0a !important;
    color: #00ff88 !important;
    font-family: 'Share Tech Mono', monospace !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #040a06 !important;
    border-right: 1px solid #00ff4440 !important;
}

/* ── Header ── */
.emiglio-header {
    text-align: center;
    padding: 1.5rem 0 1rem;
    border-bottom: 1px solid #00ff4440;
    margin-bottom: 1.5rem;
}
.emiglio-logo {
    font-family: 'Orbitron', monospace;
    font-size: 2.6rem;
    font-weight: 700;
    color: #00ff88;
    letter-spacing: 0.18em;
    text-shadow: 0 0 24px #00ff8866, 0 0 60px #00ff4422;
    margin: 0;
}
.emiglio-tagline {
    font-size: 0.75rem;
    color: #00ff4480;
    letter-spacing: 0.3em;
    margin-top: 4px;
    text-transform: uppercase;
}
.emiglio-dot {
    display: inline-block;
    width: 8px; height: 8px;
    background: #00ff88;
    border-radius: 50%;
    margin-right: 8px;
    animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
    0%,100% { opacity: 1; box-shadow: 0 0 6px #00ff88; }
    50%      { opacity: 0.3; box-shadow: none; }
}

/* ── Chat messages ── */
.msg-user {
    background: #001a0a;
    border: 1px solid #00ff4430;
    border-left: 3px solid #00ff88;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin: 8px 0;
    font-size: 0.9rem;
}
.msg-user::before {
    content: "> USER: ";
    color: #00ff4480;
    font-size: 0.72rem;
}
.msg-bot {
    background: #000d05;
    border: 1px solid #00ff4420;
    border-left: 3px solid #00cc66;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin: 8px 0;
    font-size: 0.9rem;
    white-space: pre-wrap;
}
.msg-bot::before {
    content: "EMIGLIO: ";
    color: #00cc6680;
    font-size: 0.72rem;
    display: block;
    margin-bottom: 4px;
}

/* ── Steps/workflow log ── */
.step-card {
    background: #001508;
    border: 1px solid #00ff4420;
    border-radius: 6px;
    padding: 8px 12px;
    margin: 5px 0;
    font-size: 0.78rem;
}
.step-time { color: #00ff4460; margin-right: 6px; }
.step-tool { color: #00ffaa; font-weight: bold; }
.step-desc { color: #00cc66cc; }
.step-preview {
    color: #00ff4450;
    margin-top: 3px;
    font-size: 0.72rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* ── File pills ── */
.file-pill {
    display: inline-block;
    background: #001a0a;
    border: 1px solid #00ff4440;
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 0.75rem;
    color: #00ff88;
    margin: 3px 4px 3px 0;
}

/* ── Section labels ── */
.section-label {
    font-family: 'Orbitron', monospace;
    font-size: 0.65rem;
    color: #00ff4460;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    border-bottom: 1px solid #00ff4420;
    padding-bottom: 4px;
    margin: 1rem 0 0.5rem;
}

/* ── Inputs ── */
.stTextArea textarea, .stTextInput input {
    background: #000d05 !important;
    border: 1px solid #00ff4440 !important;
    color: #00ff88 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.9rem !important;
    border-radius: 4px !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #00ff88 !important;
    box-shadow: 0 0 8px #00ff8840 !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #001a0a !important;
    color: #00ff88 !important;
    border: 1px solid #00ff4460 !important;
    border-radius: 4px !important;
    font-family: 'Orbitron', monospace !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.1em !important;
    padding: 8px 20px !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #003314 !important;
    border-color: #00ff88 !important;
    box-shadow: 0 0 12px #00ff8840 !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #040a06; }
::-webkit-scrollbar-thumb { background: #00ff4440; border-radius: 2px; }

/* Hide Streamlit elements */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)



# SESSION STATE

if "history"      not in st.session_state: st.session_state.history      = []
if "all_steps"    not in st.session_state: st.session_state.all_steps    = []
if "workspace"    not in st.session_state: st.session_state.workspace    = []
if "is_loading"   not in st.session_state: st.session_state.is_loading   = False
if "last_example" not in st.session_state: st.session_state.last_example = ""



# WORKFLOW EXAMPLES

EXAMPLES = [
    "summarize this text + extract 5 key points + save in file 'summary': AI is transforming the medical industry by enabling more accurate and faster diagnoses. Machine learning algorithms can detect patterns in medical images that the human eye might miss. However, this raises debates about data privacy and medical responsibility.",

    "create a professional email about a Friday sales meeting + translate it to English + save both versions",

    "generate a report with sections: introduction, analysis, conclusions + save it as 'monthly_report.md'",

    "search the internet for AI news in 2025 + summarize the findings + create an email with the summary",

    "calculate: print(sum(range(1, 101))) + save the result in a file 'calculation.txt'",

    "list my saved files",
]



# SIDEBAR

with st.sidebar:
    # Sidebar header
    st.markdown("""
    <div style="text-align:center;padding:1rem 0 0.5rem">
      <span class="emiglio-dot"></span>
      <span style="font-family:'Orbitron',monospace;font-size:1.1rem;color:#00ff88;letter-spacing:.15em">EMIGLIO</span>
      <div style="font-size:0.62rem;color:#00ff4460;letter-spacing:.25em;margin-top:2px">SYSTEM ONLINE</div>
    </div>
    """, unsafe_allow_html=True)

    # Workflow log
    st.markdown('<div class="section-label">⚡ Workflow Log</div>', unsafe_allow_html=True)

    if st.session_state.all_steps:
        step_container = st.container()
        with step_container:
            for step in reversed(st.session_state.all_steps[-20:]):
                st.markdown(f"""
                <div class="step-card">
                  <span class="step-time">[{step['timestamp']}]</span>
                  <span class="step-tool">{step['tool']}</span>
                  <div class="step-desc">{step['description']}</div>
                  {f'<div class="step-preview">{step["preview"]}</div>' if step.get('preview') else ''}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#00ff4440;font-size:.78rem;padding:8px 0">No steps executed yet.</div>', unsafe_allow_html=True)

    # Workspace
    st.markdown('<div class="section-label"> Workspace</div>', unsafe_allow_html=True)

    workspace_files = sorted(WORKSPACE.iterdir()) if WORKSPACE.exists() else []
    if workspace_files:
        for f in workspace_files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f'<span class="file-pill">{f.name}</span>', unsafe_allow_html=True)
            with col2:
                # Download button
                content = f.read_bytes()
                st.download_button(
                    "↓", data=content, file_name=f.name,
                    key=f"dl_{f.name}", help=f"Download {f.name}",
                    use_container_width=True,
                )
    else:
        st.markdown('<div style="color:#00ff4440;font-size:.78rem;padding:8px 0">Workspace empty.</div>', unsafe_allow_html=True)

    # Clear
    st.markdown('<div class="section-label">⚙ Controls</div>', unsafe_allow_html=True)
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.history   = []
        st.session_state.all_steps = []
        st.rerun()

    # Stats
    st.markdown(f"""
    <div style="margin-top:1rem;font-size:.7rem;color:#00ff4450;border-top:1px solid #00ff4420;padding-top:.8rem">
      Total steps: {len(st.session_state.all_steps)}<br>
      Files: {len(workspace_files)}<br>
      Messages: {len(st.session_state.history)}
    </div>
    """, unsafe_allow_html=True)



# MAIN AREA

# Header
st.markdown("""
<div class="emiglio-header">
  <p class="emiglio-logo"> 🔺EMIGLIO 🔺</p>
  <p class="emiglio-tagline">AI Workflow Automation Assistant // v2.0</p>
</div>
""", unsafe_allow_html=True)

# Chat history
chat_container = st.container()
with chat_container:
    if not st.session_state.history:
        st.markdown("""
        <div style="text-align:center;padding:3rem 2rem;color:#00ff4440">
          <div style="font-size:2.5rem;margin-bottom:1rem">⬡</div>
          <div style="font-size:.85rem;letter-spacing:.1em">
            Welcome. I’m Emiglio.<br>
            Write a task or combine multiple with "+"<br><br>
            <span style="color:#00ff4460">example: summarize + create email + save to file</span>
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state.history:
            if msg["role"] == "user":
                st.markdown(f'<div class="msg-user">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="msg-bot">{msg["content"]}</div>', unsafe_allow_html=True)



# QUICK EXAMPLES
st.markdown('<div class="section-label"> Quick examples</div>', unsafe_allow_html=True)

cols = st.columns(3)
example_labels = [
    "Summarize + extract points",
    "Email + translate",
    "Generate report",
    "Search + summarize + email",
    "Calculate with Python",
    "List files",
]
for i, (col, label, example) in enumerate(zip(cols * 2, example_labels, EXAMPLES)):
    with col:
        if st.button(label, key=f"ex_{i}", use_container_width=True):
            st.session_state.last_example = example
            st.rerun()



# USER INPUT
st.markdown('<div class="section-label">↳ Instruction for Emiglio</div>', unsafe_allow_html=True)

# If there is a preloaded example, use it as the initial value
default_text = st.session_state.last_example
st.session_state.last_example = ""  # clear after use

user_input = st.text_area(
    label="",
    value=default_text,
    placeholder='Write one or more tasks. Example: "summarize this text + create email + save to file"',
    height=100,
    key="user_input",
    label_visibility="collapsed",
)

col_send, col_clear = st.columns([1, 4])
with col_send:
    send_clicked = st.button("▶  RUN", type="primary", use_container_width=True)



# PROCESSING
if send_clicked and user_input.strip():
    # Add user message to history
    st.session_state.history.append({"role": "user", "content": user_input.strip()})

    # Loading placeholder
    with st.spinner("🔺 Emiglio processing workflow..."):
        try:
            # Build history without the last message (we already passed it as user_message)
            history_for_agent = st.session_state.history[:-1]

            result = run_workflow(
                user_message=user_input.strip(),
                history=history_for_agent,
            )

            # Save response and steps
            st.session_state.history.append({
                "role": "assistant",
                "content": result["response"]
            })
            st.session_state.all_steps.extend(result["steps"])

        except Exception as e:
            error_msg = f"Workflow error: {str(e)}"
            st.session_state.history.append({"role": "assistant", "content": error_msg})

    st.rerun()
