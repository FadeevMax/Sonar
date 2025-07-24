import streamlit as st
import os
import uuid
import json
from datetime import datetime
from streamlit_local_storage import LocalStorage
import requests
import streamlit_shadcn_ui as ui

# ----------------------- Constants -------------------------
DEFAULT_INSTRUCTIONS = """You are a cannabis industry research assistant powered by Perplexity AI tools. Your role is to help report on strain-specific data points. You will be provided with the name of a cannabis strain. Your task is to return a structured report containing 14 specific data fields, all in plain text Markdown format, as outlined below.

### If the strain is well-known
If the strain is established and information is available, conduct intelligent research using all tools at your disposal. Cross-reference reputable sources (Leafly.com (primary), CannaDB.org, Strainsdb.org, etc.) to ensure accuracy. Return the most up-to-date and complete information for the following 14 fields:

---

1. **Strain Name**
2. **Alt Name(s)**
3. **Nickname(s)**
4. **Hybridization** (Indica, Sativa or Hybrid)
5. **Lineage/Genetics**
6. **Trivia** (Interesting facts about the strain)
7. **Reported Flavors (Top 3)**
8. **Reported Effects (Top 3)**
9. **Availability by State (U.S. states where it's sold)**
10. **Awards (if any)**
11. **Original Release Date (if known)**
12. **Physical Characteristics (Color, Bud Structure, Trichomes)**
13. **Similar Strains (Top 3 by effect/genetics)**
14. **User Rating (Average Score, # of Reviews, Common Comments)**

---
### If the strain is a new hybrid and/or information is limited

If full information is not available about the strain (e.g., it's a new hybrid or rare cross). Clearly state that the original strain had insufficient data.

---
### Tone and format

- Professional, neutral, data-focused.
- Use **bullet points or line breaks** where appropriate for readability.
- If a data point is **unknown or unavailable**, state: Unknown.
"""
MODELS = [
    "sonar",
    "sonar-pro",
    "sonar-deep-research",
    "sonar-reasoning-pro",
    "mistral-7b-instruct",
]

# ------------------------------------------------------------
# 🗂  PERSISTENCE HELPERS  (Browser local‑storage via streamlit_local_storage)
# ------------------------------------------------------------

def _load_conversations(local_store: LocalStorage) -> list[dict]:
    try:
        raw = local_store.getItem("conversations") or "[]"
        return json.loads(raw)
    except Exception:
        return []


def _save_conversations(local_store: LocalStorage, conversations: list[dict]) -> None:
    try:
        local_store.setItem("conversations", json.dumps(conversations))
    except Exception:
        pass

# ------------------------------------------------------------
# 🔑  PERPLEXITY API WRAPPER
# ------------------------------------------------------------

def call_perplexity_api(messages: list[dict], model: str, api_key: str | None):
    if not api_key:
        ui.alert_dialog(
            title="Missing API Key",
            description="Please provide a Perplexity API key in Settings → API Key",
            confirm_label="OK"
        )
        return None

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 4000,
        "temperature": 0.2,
        "top_p": 0.9,
        "stream": False,
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        ui.alert_dialog(
            title="API Error",
            description=str(e),
            confirm_label="OK"
        )
        return None

# ------------------------------------------------------------
# 🔄  SESSION INITIALISATION
# ------------------------------------------------------------

def init_session_state():
    defaults = {
        "authenticated": False,
        "api_key": None,
        "model": MODELS[0],
        "instructions": DEFAULT_INSTRUCTIONS,
        "custom_instructions": {"Default": DEFAULT_INSTRUCTIONS},
        "current_instruction_name": "Default",
        "conversations": [],
        "current_conv_id": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ------------------------------------------------------------
# 📑  CONVERSATION UTILITIES
# ------------------------------------------------------------

def _ensure_conversation(localS: LocalStorage):
    if not st.session_state.conversations:
        new_id = str(uuid.uuid4())
        st.session_state.conversations = [{"id": new_id, "title": "New Conversation", "messages": []}]
        _save_conversations(localS, st.session_state.conversations)
    if st.session_state.current_conv_id is None:
        st.session_state.current_conv_id = st.session_state.conversations[0]["id"]


def _get_current_conv():
    for c in st.session_state.conversations:
        if c["id"] == st.session_state.current_conv_id:
            return c
    return None

# ------------------------------------------------------------
# 🔐  AUTH
# ------------------------------------------------------------
def login_form():
    ui.card(title="🔐 Login", key="login_card")
    cred = ui.input(placeholder="Enter Perplexity API key or password", type="password", key="cred")
    if ui.button("Login", key="login_btn"):
        if cred and cred.startswith("pplx-"):
            st.session_state.api_key = cred
            st.session_state.authenticated = True
            st.experimental_rerun()
        elif cred and cred == st.secrets.get("PASSWORD"):
            default_key = st.secrets.get("PERPLEXITY_API_KEY")
            if default_key:
                st.session_state.api_key = default_key
                st.session_state.authenticated = True
                st.experimental_rerun()
            else:
                ui.alert_dialog(
                    title="Error",
                    description="Default API key missing in st.secrets",
                    confirm_label="OK"
                )
        else:
            ui.alert_dialog(
                title="Invalid Credentials",
                description="❌ Invalid key or password",
                confirm_label="OK"
            )

# ------------------------------------------------------------
# 🖥️  SIDEBAR
# ------------------------------------------------------------

def sidebar_conversations(localS: LocalStorage):
    ui.card(title="📚 Conversations", key="conv_card")
    filter_text = ui.input(placeholder="Search…", key="conv_search")
    for conv in st.session_state.conversations:
        title = conv["title"] or "Untitled"
        if filter_text.lower() in title.lower():
            if ui.button(title, key=f"conv_{conv['id']}"):
                st.session_state.current_conv_id = conv["id"]
                st.experimental_rerun()
    if ui.button("➕ New Conversation", key="new_conv_btn"):
        new_id = str(uuid.uuid4())
        st.session_state.conversations.insert(0, {"id": new_id, "title": "New Conversation", "messages": []})
        st.session_state.current_conv_id = new_id
        _save_conversations(localS, st.session_state.conversations)
        st.experimental_rerun()

# ------------------------------------------------------------
# 🤖  CHAT PAGE
# ------------------------------------------------------------

def chat_page(localS: LocalStorage):
    conv = _get_current_conv()
    if conv is None:
        st.error("Conversation not found.")
        return

    ui.card(title="🤖 AI Research Assistant", key="chat_card")
    ui.element(f"Model → {st.session_state.model}")

    # Display history
    for msg in conv["messages"]:
        with ui.card(key=f"msg_{uuid.uuid4()}"):
            ui.element(className="flex items-center gap-2")(
                avatar(src=f"/avatars/{msg['role']}.png", alt=msg['role'], size="sm"),
                lambda: st.markdown(msg["content"]),
            )

    # User input
    user_input = ui.textarea(placeholder="Ask your question…", key="user_input")
    if ui.button("Send", key="send_btn") and user_input:
        conv["messages"].append({"role": "user", "content": user_input})
        if conv["title"] == "New Conversation":
            conv["title"] = user_input.strip().split("\n")[0][:40]
        _save_conversations(localS, st.session_state.conversations)

        with st.spinner("Thinking & researching …"):
            assistant_reply = call_perplexity_api(
                [{"role": "system", "content": st.session_state.instructions}] + conv["messages"],
                st.session_state.model,
                st.session_state.api_key,
            )
        if assistant_reply:
            conv["messages"].append({"role": "assistant", "content": assistant_reply})
            _save_conversations(localS, st.session_state.conversations)
            st.experimental_rerun()

# ------------------------------------------------------------
# 📄  INSTRUCTIONS PAGE
# ------------------------------------------------------------

def instructions_page():
    ui.card(title="📄 Instructions Manager", key="instr_card")
    names = list(st.session_state.custom_instructions.keys())
    selected = ui.select(options=names, default_value=st.session_state.current_instruction_name, key="instr_select")
    st.session_state.current_instruction_name = selected
    st.session_state.instructions = st.session_state.custom_instructions[selected]
    edited = ui.textarea(value=st.session_state.instructions, height=300, key="instr_edit")
    if ui.button("Save Instructions", key="save_instr_btn"):
        st.session_state.custom_instructions[selected] = edited
        st.session_state.instructions = edited
        ui.alert_dialog(
            title="Saved",
            description="Instructions saved successfully 📝",
            confirm_label="OK"
        )

# ------------------------------------------------------------
# ⚙️  SETTINGS PAGE
# ------------------------------------------------------------

def settings_page():
    ui.card(title="⚙️ Settings", key="settings_card")
    model_choice = ui.select(options=MODELS, default_value=st.session_state.model, key="model_select")
    st.session_state.model = model_choice
    key_input = ui.input(placeholder="Perplexity API Key", type="password", key="api_key_input")
    if key_input and key_input != st.session_state.api_key:
        st.session_state.api_key = key_input
        ui.alert_dialog(
            title="API Key Updated",
            description="API key updated successfully ✅",
            confirm_label="OK"
        )
    if ui.button("Clear Current Conversation", key="clear_conv_btn"):
        conv = _get_current_conv()
        if conv:
            conv["messages"] = []
            _save_conversations(LocalStorage(), st.session_state.conversations)
            st.experimental_rerun()

# ------------------------------------------------------------
# 🚀  MAIN
# ------------------------------------------------------------

def main():
    st.set_page_config(page_title="AI Research Assistant", page_icon="🤖", layout="wide")
    localS = LocalStorage()
    init_session_state()
    if not st.session_state.conversations:
        st.session_state.conversations = _load_conversations(localS)
    _ensure_conversation(localS)

    with st.sidebar:
        if not st.session_state.authenticated:
            login_form()
            st.stop()
        sidebar_conversations(localS)

    tab = ui.tabs(options=["🤖 Chat", "📄 Instructions", "⚙️ Settings"], default_value="🤖 Chat", key="main_tabs")
    if tab == "🤖 Chat":
        chat_page(localS)
    elif tab == "📄 Instructions":
        instructions_page()
    elif tab == "⚙️ Settings":
        settings_page()

if __name__ == "__main__":
    main()
