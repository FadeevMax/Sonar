import streamlit as st
import time
import os
import uuid
from datetime import datetime
import json
from streamlit_local_storage import LocalStorage
import requests

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
    """Return a list of stored conversations [{id,title,messages:[{role,content}]}]."""
    try:
        raw = local_store.getItem("conversations") or "[]"
        return json.loads(raw)
    except Exception:
        return []

def _save_conversations(local_store: LocalStorage, conversations: list[dict]) -> None:
    """Persist conversations list back to the browser."""
    try:
        local_store.setItem("conversations", json.dumps(conversations))
    except Exception:
        pass  # Best‑effort only – if it fails we still keep runtime state

# ------------------------------------------------------------
# 🔑  PERPLEXITY API WRAPPER
# ------------------------------------------------------------

def call_perplexity_api(messages: list[dict], model: str, api_key: str | None):
    if not api_key:
        st.error("⛔ Please provide a Perplexity API key in Settings → API Key")
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
        st.error(f"API Error → {e}")
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
        # Conversation handling
        "conversations": [],       # loaded from local‑storage
        "current_conv_id": None,   # uuid4 string of selected conversation
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ------------------------------------------------------------
# 📑  CONVERSATION UTILITIES
# ------------------------------------------------------------

def _ensure_conversation(localS: LocalStorage):
    """Guarantee that there is at least one conversation and a selected id."""
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
# 🖥️  UI COMPONENTS
# ------------------------------------------------------------

def sidebar_conversations(localS: LocalStorage):
    st.sidebar.header("📚 Conversations")
    titles = [c["title"] if c["title"] else "Untitled" for c in st.session_state.conversations]
    selected_index = next((i for i, c in enumerate(st.session_state.conversations)
                           if c["id"] == st.session_state.current_conv_id), 0)
    choice = st.sidebar.radio("Select", titles, index=selected_index, key="conv_radio")
    st.session_state.current_conv_id = st.session_state.conversations[titles.index(choice)]["id"]

    if st.sidebar.button("➕  New Conversation"):
        new_id = str(uuid.uuid4())
        st.session_state.conversations.insert(0, {"id": new_id, "title": "New Conversation", "messages": []})
        st.session_state.current_conv_id = new_id
        _save_conversations(localS, st.session_state.conversations)
        st.rerun()


def chat_page(localS: LocalStorage):
    conv = _get_current_conv()
    if conv is None:
        st.error("Conversation not found.")
        return

    st.title("🤖 AI Research Assistant")
    st.caption(f"Model → {st.session_state.model}")

    # Display history
    for msg in conv["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User input
    if user_input := st.chat_input("Ask your question..."):
        conv["messages"].append({"role": "user", "content": user_input})

        # Rename conversation if it's still using the default title
        if conv["title"] == "New Conversation":
            conv["title"] = user_input.strip().split("\n")[0][:40]

        with st.chat_message("user"):
            st.markdown(user_input)

        api_messages = ([{"role": "system", "content": st.session_state.instructions}] + conv["messages"])
        with st.spinner("Thinking & researching ..."):
            assistant_reply = call_perplexity_api(api_messages, st.session_state.model, st.session_state.api_key)

        if assistant_reply:
            conv["messages"].append({"role": "assistant", "content": assistant_reply})
            with st.chat_message("assistant"):
                st.markdown(assistant_reply)

        # Persist updated conversations
        _save_conversations(localS, st.session_state.conversations)


def instructions_page():
    st.header("📄 Instructions Manager")
    names = list(st.session_state.custom_instructions.keys())
    idx = names.index(st.session_state.current_instruction_name)
    selected = st.selectbox("Select", names, index=idx)
    st.session_state.current_instruction_name = selected
    st.session_state.instructions = st.session_state.custom_instructions[selected]

    edited = st.text_area("Instruction Content", st.session_state.instructions, height=300,
                          key="instr_edit")
    if st.button("Save"):
        st.session_state.custom_instructions[selected] = edited
        st.session_state.instructions = edited
        st.success("Saved 📝")


def settings_page():
    st.header("⚙️ Settings")
    model_choice = st.selectbox("Model", MODELS, index=MODELS.index(st.session_state.model))
    st.session_state.model = model_choice

    key = st.text_input("Perplexity API Key", type="password", value=st.session_state.api_key or "")
    if key and key != st.session_state.api_key:
        st.session_state.api_key = key
        st.success("API key updated ✅")

    if st.button("Clear current conversation"):
        conv = _get_current_conv()
        if conv:
            conv["messages"] = []
            _save_conversations(LocalStorage(), st.session_state.conversations)
            st.rerun()
def login_form():
    """
    Presents a single password field.
    • If the input starts with 'pplx-' → treat as Perplexity API key.
    • Else, if it matches st.secrets['PASSWORD'] → use the default
      key from st.secrets['PERPLEXITY_API_KEY'].
    Sets st.session_state.authenticated + .api_key on success.
    """
    st.subheader("🔐 Login")
    cred = st.text_input(
        "Enter Perplexity API key *or* password", type="password"
    )

    if st.button("Login"):
        # 1️⃣ Direct API‑key path
        if cred and cred.startswith("pplx-"):
            st.session_state.api_key = cred
            st.session_state.authenticated = True
            st.success("✅ Logged in with API key")
            st.rerun()

        # 2️⃣ Password → fallback key path
        elif cred and cred == st.secrets.get("PASSWORD"):
            default_key = st.secrets.get("PERPLEXITY_API_KEY")
            if default_key:
                st.session_state.api_key = default_key
                st.session_state.authenticated = True
                st.success("✅ Logged in with default key")
                st.rerun()
            else:
                st.error("Default API key missing in `st.secrets`")

        # 3️⃣ Invalid input
        else:
            st.error("❌ Invalid key or password")
# ------------------------------------------------------------
# 🚀  MAIN
# ------------------------------------------------------------

def main():
    st.set_page_config("AI Research Assistant", "🤖", layout="wide")
    localS = LocalStorage()

    init_session_state()

    # Load stored conversations once per session
    if not st.session_state.conversations:
        st.session_state.conversations = _load_conversations(localS)

    _ensure_conversation(localS)

    # --- Sidebar content (login & conv list) ---
    with st.sidebar:
        if not st.session_state.authenticated:
            login_form()     # …and call the helper here
            st.stop()

        sidebar_conversations(localS)
        st.markdown("---")
        page = st.radio("Nav", ["🤖 Chat", "📄 Instructions", "⚙️ Settings"], key="nav_radio")

    # --- Main area ---
    if page == "🤖 Chat":
        chat_page(localS)
    elif page == "📄 Instructions":
        instructions_page()
    elif page == "⚙️ Settings":
        settings_page()


if __name__ == "__main__":
    main()
