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

CONVERSATIONS_KEY_TEMPLATE = "conversations_{user_id}"

# ----------------------- Helpers for Conversation Persistence -------------------------

def load_conversations(local_storage, user_id):
    """Load all conversations for a given user from LocalStorage."""
    key = CONVERSATIONS_KEY_TEMPLATE.format(user_id=user_id)
    try:
        raw = local_storage.getItem(key)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return []


def save_conversations(local_storage, user_id, conversations):
    """Save conversations list back to LocalStorage."""
    key = CONVERSATIONS_KEY_TEMPLATE.format(user_id=user_id)
    try:
        local_storage.setItem(key, json.dumps(conversations))
    except Exception:
        pass


def ensure_current_conversation():
    """Ensure a current conversation exists and keep session_state in sync."""
    if "current_conv_id" not in st.session_state:
        # No conversation selected yet -> pick the first one
        if st.session_state.conversations:
            st.session_state.current_conv_id = st.session_state.conversations[0]["id"]
        else:
            new_conv_id = str(uuid.uuid4())
            st.session_state.conversations = [{
                "id": new_conv_id,
                "title": "New Conversation",
                "messages": [],
            }]
            st.session_state.current_conv_id = new_conv_id
    # Sync st.session_state.messages with the selected conversation
    current_conv = next(c for c in st.session_state.conversations if c["id"] == st.session_state.current_conv_id)
    st.session_state.messages = current_conv["messages"]


# ----------------------- Initialization -------------------------

def get_persistent_user_id(local_storage):
    try:
        user_id = local_storage.getItem("user_id")
        if not user_id:
            user_id = str(uuid.uuid4())
            local_storage.setItem("user_id", user_id)
        return user_id
    except Exception:
        return str(uuid.uuid4())


def initialize_session_state(local_storage):
    # First get / set user_id so we can load their stored conversations
    if "user_id" not in st.session_state:
        st.session_state.user_id = get_persistent_user_id(local_storage)

    # Load any previously saved conversations (only once per session)
    if "conversations" not in st.session_state:
        st.session_state.conversations = load_conversations(local_storage, st.session_state.user_id)

    # Default-level session keys
    defaults = {
        "authenticated": False,
        "api_key": None,
        "custom_instructions": {"Default": DEFAULT_INSTRUCTIONS},
        "current_instruction_name": "Default",
        "state_loaded": True,
        "model": MODELS[0],
        "instructions": DEFAULT_INSTRUCTIONS,
        "instruction_edit_mode": "view",
        "sidebar_expanded": True,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Guarantee there is a current conversation in place
    ensure_current_conversation()


# ----------------------- API Handler -------------------------

def call_perplexity_api(messages, model, api_key):
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
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 400:
            st.error("❌ Bad request: The API payload may be malformed. Check formatting and field names.")
            st.json(response.json())
            return None
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None


# ----------------------- UI Components -------------------------

def sidebar_conversation_selector(localS):
    """Sidebar component to list & switch between conversations, create new ones, or delete."""
    st.sidebar.subheader("💬 Conversations")

    # Titles for listbox
    titles = [conv["title"] for conv in st.session_state.conversations]
    # Keep mapping title to id (not unique if user reuses title, but ok for simple use)
    selected_idx = 0
    if st.session_state.current_conv_id:
        for i, c in enumerate(st.session_state.conversations):
            if c["id"] == st.session_state.current_conv_id:
                selected_idx = i
                break

    selected_title = st.sidebar.selectbox("Select a conversation", titles, index=selected_idx, key="conv_select")

    # Update current conversation if changed
    selected_conv = st.session_state.conversations[titles.index(selected_title)]
    if selected_conv["id"] != st.session_state.current_conv_id:
        st.session_state.current_conv_id = selected_conv["id"]
        st.session_state.messages = selected_conv["messages"]

    # Buttons for new conversation or delete
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("➕ New"):
            new_id = str(uuid.uuid4())
            st.session_state.conversations.insert(0, {"id": new_id, "title": "New Conversation", "messages": []})
            st.session_state.current_conv_id = new_id
            st.session_state.messages = []
            save_conversations(localS, st.session_state.user_id, st.session_state.conversations)
            st.experimental_rerun()
    with col2:
        if st.button("🗑️ Delete"):
            # Delete current conversation
            st.session_state.conversations = [c for c in st.session_state.conversations if c["id"] != st.session_state.current_conv_id]
            # After delete, reset current to first or create new
            if st.session_state.conversations:
                st.session_state.current_conv_id = st.session_state.conversations[0]["id"]
                st.session_state.messages = st.session_state.conversations[0]["messages"]
            else:
                new_id = str(uuid.uuid4())
                st.session_state.conversations = [{"id": new_id, "title": "New Conversation", "messages": []}]
                st.session_state.current_conv_id = new_id
                st.session_state.messages = []
            save_conversations(localS, st.session_state.user_id, st.session_state.conversations)
            st.experimental_rerun()



def display_chat(localS):
    st.title("🤖 AI Research Assistant")
    st.subheader(f"Model: {st.session_state.model}")

    # Display past messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if user_input := st.chat_input("Ask your question here..."):
        # Append user message locally
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Update title if this is the first user message in the conversation
        current_conv = next(c for c in st.session_state.conversations if c["id"] == st.session_state.current_conv_id)
        if current_conv["title"] in ("New Conversation", ""):
            current_conv["title"] = user_input[:50]  # Truncate for sidebar

        # Build API messages
        api_messages = [
            {"role": "system", "content": st.session_state.instructions}
        ] + st.session_state.messages

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)

        # Call API
        with st.spinner("Thinking and researching..."):
            response = call_perplexity_api(api_messages, st.session_state.model, st.session_state.api_key)

        if response:
            # Append assistant message
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
        else:
            st.error("❌ Failed to get response from Perplexity API")

        # Save changes to localStorage
        current_conv["messages"] = st.session_state.messages
        save_conversations(localS, st.session_state.user_id, st.session_state.conversations)


def instructions_page():
    st.header("📄 Instructions Manager")
    if st.session_state.instruction_edit_mode == "create":
        with st.form("new_instruction_form"):
            name = st.text_input("Instruction Name")
            content = st.text_area("Content", height=300)
            if st.form_submit_button("Save"):
                if name and content and name not in st.session_state.custom_instructions:
                    st.session_state.custom_instructions[name] = content
                    st.session_state.current_instruction_name = name
                    st.session_state.instructions = content
                    st.session_state.instruction_edit_mode = "view"
                    st.success(f"✅ Saved '{name}'")
                    st.rerun()
        if st.button("Cancel"):
            st.session_state.instruction_edit_mode = "view"
            st.rerun()
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            options = list(st.session_state.custom_instructions.keys())
            selected_index = options.index(st.session_state.current_instruction_name)
            selected = st.selectbox("Select Instruction", options, index=selected_index)
            st.session_state.current_instruction_name = selected
            st.session_state.instructions = st.session_state.custom_instructions[selected]
        with col2:
            st.write("")  # Spacer
            st.write("")  # Spacer
            if st.button("New Instruction"):
                st.session_state.instruction_edit_mode = "create"
                st.rerun()

        content_key = f"instruction_content_{selected}"
        edited_content = st.text_area(
            "Instruction Content",
            value=st.session_state.custom_instructions[selected],
            height=300,
            disabled=(selected == "Default"),
            key=content_key,
        )

        if selected != "Default":
            col1_btn, col2_btn, _ = st.columns([1, 1, 5])
            with col1_btn:
                if st.button("Save Changes"):
                    st.session_state.custom_instructions[selected] = edited_content
                    st.success("✅ Changes saved")
                    st.rerun()
            with col2_btn:
                if st.button("Delete"):
                    del st.session_state.custom_instructions[selected]
                    st.session_state.current_instruction_name = "Default"
                    st.session_state.instructions = st.session_state.custom_instructions["Default"]
                    st.success("✅ Deleted")
                    st.rerun()


def settings_page(localS):
    st.header("⚙️ Settings")
    selected = st.selectbox("Choose a model", MODELS, index=MODELS.index(st.session_state.model))
    if selected != st.session_state.model:
        st.session_state.model = selected
        st.success(f"✅ Switched to {selected}")

    if st.button("Clear Current Conversation"):
        # Clears only the current conversation's messages
        current_conv = next(c for c in st.session_state.conversations if c["id"] == st.session_state.current_conv_id)
        current_conv["messages"] = []
        st.session_state.messages = []
        save_conversations(localS, st.session_state.user_id, st.session_state.conversations)
        st.success("✅ Cleared chat")


# ----------------------- Main -------------------------

def main():
    st.set_page_config("AI Research Assistant", "🤖", layout="wide")
    localS = LocalStorage()

    # Initialize session & load data
    initialize_session_state(localS)

    # ----------------------- Login Screen -----------------------
    if not st.session_state.authenticated:
        st.title("🔐 Login")
        key_input = st.text_input("Enter Perplexity API key or password", type="password")
        if st.button("Login"):
            if key_input and key_input.startswith("pplx-"):
                st.session_state.api_key = key_input
                st.session_state.authenticated = True
                st.success("✅ Logged in with API key")
                st.experimental_rerun()
            elif key_input == st.secrets.get("PASSWORD"):
                st.session_state.api_key = st.secrets["PERPLEXITY_API_KEY"]
                st.session_state.authenticated = True
                st.success("✅ Logged in with default key")
                st.experimental_rerun()
            else:
                st.error("❌ Invalid key or password")
        with st.expander("Where to find your API key"):
            st.markdown("Go to the [Perplexity AI Website](https://www.perplexity.ai/), log in to your account, navigate to API settings, and generate a new key.")
        return  # Don’t proceed unless authenticated

    # ----------------------- Sidebar -----------------------
    sidebar_conversation_selector(localS)
    page = st.sidebar.radio("Navigate", ["🤖 Chatbot", "📄 Instructions", "⚙️ Settings"])

    if page == "🤖 Chatbot":
        display_chat(localS)
    elif page == "📄 Instructions":
        instructions_page()
    elif page == "⚙️ Settings":
        settings_page(localS)


# ----------------------- Run -------------------------
if __name__ == "__main__":
    main()
