import streamlit as st
import requests
import time
import uuid
import os

# Configuration
AGENT_BASE_URL = os.getenv("AGENT_URL", "http://127.0.0.1:8081").replace("/chat", "")
MD_DIR = "md"

st.set_page_config(
    page_title="Agentic AI for Pathway Engineering",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp { font-family: 'Inter', sans-serif; }
    textarea[aria-label="Input Query"] { min-height: 120px; font-family: 'Inter', sans-serif; }
    .kb-content { background-color: #f0f2f6; padding: 15px; border-radius: 8px; margin-top: 10px; margin-bottom: 20px; font-size: 0.9em; }
    @media (prefers-color-scheme: dark) { .kb-content { background-color: #262730; } }
</style>
""", unsafe_allow_html=True)

# Helper Functions
def load_markdown(filename):
    filepath = os.path.join(MD_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File {filename} not found."

def create_new_session():
    new_id = str(uuid.uuid4())
    if "sessions" not in st.session_state:
        st.session_state.sessions = {}
    
    st.session_state.sessions[new_id] = {
        "title": f"New Chat {new_id[:4]}",
        "messages": [{
            "role": "assistant", 
            "content": "Hello! I am ready to assist with pathway engineering tasks.",
            "logs": []
        }]
    }
    st.session_state.current_session_id = new_id
    st.session_state.input_buffer = ""
    st.session_state.kb_view = None

def switch_session(session_id):
    st.session_state.current_session_id = session_id
    st.session_state.input_buffer = ""

def apply_template(template_text):
    st.session_state.input_buffer = template_text

# Initialization Check
if "sessions" not in st.session_state:
    create_new_session()

# SIDEBAR LAYOUT
with st.sidebar:
    st.title("Pathway Eng. AI")
    
    st.markdown("### Chat Management")
    if st.button("+ New Chat", use_container_width=True, type="primary"):
        create_new_session()
        st.rerun()

    st.markdown("---")
    st.markdown("**History:**")
    session_ids = list(st.session_state.sessions.keys())

    for s_id in reversed(session_ids): 
        s_data = st.session_state.sessions[s_id]
        col_name, col_del = st.columns([0.85, 0.15])

        with col_name:
            label = s_data['title']
            if s_id == st.session_state.current_session_id:
                st.button(f"> {label}", key=f"btn_{s_id}", use_container_width=True, disabled=True)
            else:
                if st.button(label, key=f"btn_{s_id}", use_container_width=True):
                    switch_session(s_id)
                    st.rerun()

        with col_del:
            if st.button("X", key=f"del_{s_id}", help="Delete this chat"):
                del st.session_state.sessions[s_id]
                if s_id == st.session_state.current_session_id:
                    if st.session_state.sessions:
                        switch_session(list(st.session_state.sessions.keys())[0])
                    else:
                        create_new_session()
                st.rerun()

    st.markdown("---")
    st.markdown("### Knowledge Base")
    col_kb1, col_kb2 = st.columns(2)
    with col_kb1:
        if st.button("Tool Info", use_container_width=True):
            st.session_state.kb_view = "tool_description.md"
    with col_kb2:
        if st.button("Database", use_container_width=True):
            st.session_state.kb_view = "database_links.md"

    if st.session_state.kb_view:
        st.markdown(f"<div class='kb-content'>{load_markdown(st.session_state.kb_view)}</div>", unsafe_allow_html=True)

# MAIN CHAT LAYOUT
st.header("Agentic AI System")
st.caption("Context-aware reasoning for pathway engineering")

current_session = st.session_state.sessions[st.session_state.current_session_id]
messages = current_session["messages"]

# 1. Chat History Area
chat_container = st.container()
with chat_container:
    for msg in messages:
        with st.chat_message(msg["role"]):
            if msg.get("logs"):
                with st.expander("View Tool Execution Logs (Internal)"):
                    for log in msg["logs"]:
                        st.markdown(f"```text\n{log}\n```")
            st.markdown(msg["content"])

# 2. Template Shortcuts
st.markdown("---")
st.markdown("Quick Input Templates:")
t_col1, t_col2 = st.columns(2)
with t_col1:
    if st.button("dGPredictor", key="tpl_thermo", use_container_width=True):
        apply_template("Calculate dG for reaction: C00022 + C00004 + C00080 <=> C00186 + C00003")
        st.rerun()
with t_col2:
    if st.button("EnzRank", key="tpl_enzrank", use_container_width=True):
        apply_template("""Please calculate the EnzRank compatibility score for:
Enzyme: MTKRVLVTGGAGFLGSHLCERLLSEGHEVICLDNFGSGRRKNIKEFEDHPSFKVNDRDVRISESLPSVDRIYHLASRASPADFTQFPVNIALANTQGTRRLLDQARACDARMVFASTSEVYGDPKVHPQPETYTGNVNIRGARGCYDESKRFGETLTVAYQRKYDVDARTVRIFNTYGPRMRPDDGRVVPTFVTQALRGDDLTIYGDGEQTRSFCYVDDLIEGLISLMRVDNPEHNVYNIGKENERTIKELAYEVLGLTDTESDIVYEPLPEDDPGQRRPDITRAKTELDWEPKISLREGLEDTITYFDN
Substrate: C00149""")
        st.rerun()

# 3. Input Form
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_area(
        "Input Query",
        value=st.session_state.input_buffer,
        height=120,
        placeholder="Type your message here... [Ctrl + Enter] to Send [Enter] for new line",
        key="widget_input"
    )
    
    col_submit, _ = st.columns([1, 6])
    with col_submit:
        submit_button = st.form_submit_button("Send")

# 4. Processing Logic
if submit_button and user_input.strip():
    st.session_state.input_buffer = ""
    current_session["messages"].append({"role": "user", "content": user_input})
    
    if len(current_session["messages"]) == 2:
        title_text = user_input.strip().split('\n')[0]
        current_session["title"] = (title_text[:18] + "..") if len(title_text) > 18 else title_text
    
    st.rerun()

# 5. AI Execution Logic
if messages and messages[-1]["role"] == "user":
    
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        with st.spinner("Agent is reasoning in the background..."):
            try:
                payload = {
                    "query": messages[-1]["content"],
                    "thread_id": st.session_state.current_session_id
                }
                response = requests.post(f"{AGENT_BASE_URL}/chat", json=payload, timeout=300)

                if response.status_code == 200:
                    res_json = response.json()
                    final_res = res_json.get("response", "No response content.")
                    logs = res_json.get("logs", [])

                    if logs:
                        with st.expander("View Tool Execution Logs (Internal)"):
                            for log in logs:
                                st.markdown(f"```text\n{log}\n```")

                    response_placeholder.markdown(final_res)
                    current_session["messages"].append({
                        "role": "assistant",
                        "content": final_res,
                        "logs": logs 
                    })
                    
                    time.sleep(0.1)
                    st.rerun()
                else:
                    err = f"Error {response.status_code}: {response.text}"
                    response_placeholder.error(err)
                    current_session["messages"].append({"role": "assistant", "content": err})

            except Exception as e:
                err_msg = f"Error: {str(e)}"
                response_placeholder.error(err_msg)
                current_session["messages"].append({"role": "assistant", "content": err_msg})