import streamlit as st
from streamlit_shadcn_ui import input, slider, switch, button, card, tabs
import time
import os
import uuid
import json
from datetime import datetime
from streamlit_local_storage import LocalStorage
import requests

# Load logo if available
LOGO_PATH = "ChatGPT Image Jul 24, 2025 at 02_46_10 PM.png"  # You can change this to a URL too

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

---
**(Example for a Successful Primary Search)**

**User input:** "gg #4"

**Example Output:**  

**Strain Name:** GG #4

**Alt Name(s):** Original Glue, Gorilla Glue #4, Glue

**Nickname(s):** GG4, The Glue, Couch-Glue

**Hybridization:** Hybrid

**Lineage / Genetics:** Chem’s Sister × Sour Dubb × Chocolate Diesel (phenotype #4 selected by Joesy Whales & Lone Watie of GG Strains)

**Trivia (Interesting Facts):**
- Discovered accidentally when a hermaphroditic Chem’s Sister pollinated Sour Dubb plants; the keeper seed became phenotype #4—hence “#4” in the name.
- Named “Gorilla Glue” for the ultra-sticky resin that “glued” trimming scissors together during harvest.
- Forced to rebrand as “Original Glue / GG4” after trademark litigation with Gorilla Glue adhesive company (2017).

**Reported Flavors:**
- Earthy / Pungent Diesel
- Pine & Hash Spice
- Chocolate / Coffee undertone

**Reported Effects:**
- Heavy euphoria → deep relaxation (“couch-lock”)
- Sleepiness & hunger
- Mood elevation / stress relief

**Availability by State:** Widely distributed; regularly stocked in adult-use or medical markets including CA, CO, NV, WA, OR, MI, MA, IL, AZ, OK, NJ, NY and many others.

**Awards:**
- 1st Place Hybrid – High Times Cannabis Cup Michigan 2014
- 1st Place Hybrid – High Times Cannabis Cup Los Angeles 2014
- 1st Place – High Times World Cup Jamaica 2015

**Original Release Date:** Phenotype selected and released to market circa 2013; major Cup wins in 2014 established popularity.

**Physical Characteristics (Color, Bud Structure, Trichomes):**
- Dense, medium-green buds with lime & olive hues
- Thick blanket of milky trichomes giving a silvery-white frost
- Sparse but vivid orange pistils
- Extremely sticky resin glands (scissor-clogging).

**Similar Strains:**
- GG #5 (Sister Glue) – same breeding program
- Chem D – shared Chemdawg lineage / pungent diesel profile
- Sour Diesel – similar sour-fuel aroma and uplifting head rush

**User Rating:**
- Leafly average: 4.6 / 5 from 5,400 + user reviews
- Common remarks: “instant head euphoria then body melt,” “sticky buds,” strong relief for stress, pain, insomnia; some note dry mouth & anxious onset at high doses.

---
**(Example for a Fallback Scenario)**

Insufficient data for strain 'Galactic Runtz'. Contact web@headquarters.co"""
MODELS = [
    "sonar", "sonar-pro", "sonar-deep-research", "sonar-reasoning-pro", "mistral-7b-instruct"
]

def get_persistent_user_id(local_storage):
    try:
        user_id = local_storage.getItem("user_id")
        if not user_id:
            user_id = str(uuid.uuid4())
            local_storage.setItem("user_id", user_id)
        return user_id
    except:
        return str(uuid.uuid4())

def initialize_session_state():
    defaults = {
        "authenticated": False,
        "custom_instructions": {"Default": DEFAULT_INSTRUCTIONS},
        "current_instruction_name": "Default",
        "state_loaded": True,
        "model": MODELS[0],
        "instructions": DEFAULT_INSTRUCTIONS,
        "messages": [],
        "instruction_edit_mode": "view",
        "sidebar_expanded": True,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def call_perplexity_api(messages, model, api_key):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model, "messages": messages, "max_tokens": 4000,
        "temperature": 0.2, "top_p": 0.9, "stream": False
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 400:
            st.error("❌ Bad request: malformed payload.")
            st.json(response.json())
            return None
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

# ---------------------- UI COMPONENTS -----------------------

def style_app():
    st.markdown("""
    <style>
        html, body, [class*="st-"] {
            background-color: #0f0f0f;
            color: #f4f4f4;
        }
        .stButton>button {
            background-color: #ffffff10;
            color: #f4f4f4;
            border: 1px solid #666;
        }
        .stTextInput>div>input, .stTextArea>div>textarea {
            background-color: #1a1a1a;
            color: #f4f4f4;
        }
    </style>
    """, unsafe_allow_html=True)

def render_logo():
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=140)
    else:
        st.markdown("### 🧪 AI Research Assistant")

def display_chat():
    render_logo()
    st.subheader(f"💬 Model: `{st.session_state.model}`")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Ask your strain question..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"): st.markdown(user_input)

        api_messages = [{"role": "system", "content": st.session_state.instructions}] + st.session_state.messages
        with st.spinner("Researching..."):
            response = call_perplexity_api(api_messages, st.session_state.model, st.session_state.api_key)

        if response:
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                card("Strain Report", response, key=str(uuid.uuid4()))
        else:
            st.error("❌ No response received.")

def instructions_page():
    st.header("📄 Instruction Manager")
    col1, col2 = st.columns([3, 1])
    options = list(st.session_state.custom_instructions.keys())

    with col1:
        selected = st.selectbox("Choose instruction", options, index=options.index(st.session_state.current_instruction_name))
        st.session_state.current_instruction_name = selected

    with col2:
        if st.button("➕ New"):
            st.session_state.instruction_edit_mode = "create"
            st.rerun()

    if st.session_state.instruction_edit_mode == "create":
        with st.form("new_instruction_form"):
            name = st.text_input("Instruction Name")
            content = st.text_area("Paste instruction", height=300)
            if st.form_submit_button("Save"):
                if name and content:
                    st.session_state.custom_instructions[name] = content
                    st.session_state.current_instruction_name = name
                    st.session_state.instructions = content
                    st.session_state.instruction_edit_mode = "view"
                    st.success("✅ Saved.")
                    st.rerun()
        if st.button("Cancel"):
            st.session_state.instruction_edit_mode = "view"
            st.rerun()
    else:
        st.text_area("Instruction Preview", value=st.session_state.custom_instructions[selected], height=300, disabled=True)
        if selected != "Default":
            if st.button("📝 Save"):
                st.session_state.custom_instructions[selected] = st.session_state.custom_instructions[selected]
            if st.button("🗑️ Delete"):
                del st.session_state.custom_instructions[selected]
                st.session_state.current_instruction_name = "Default"
                st.success("✅ Deleted")
                st.rerun()

def settings_page():
    st.header("⚙️ Settings")
    st.write("Select your preferred LLM and clear chat memory.")
    model = st.selectbox("Choose a model", MODELS, index=MODELS.index(st.session_state.model))
    if model != st.session_state.model:
        st.session_state.model = model
        st.success("✅ Model updated.")
    if st.button("🧹 Clear Conversation"):
        st.session_state.messages = []
        st.success("✅ Chat reset.")

# ---------------------- MAIN APP -----------------------------

def main():
    st.set_page_config("AI Research Assistant", "🤖", layout="wide")
    style_app()

    localS = LocalStorage()
    st.session_state.user_id = get_persistent_user_id(localS)
    initialize_session_state()

    if not st.session_state.authenticated:
        st.title("🔐 Login")
        key = st.text_input("Perplexity API Key", type="password")
        if st.button("Login"):
            if key.startswith("pplx-"):
                st.session_state.api_key = key
                st.session_state.authenticated = True
                st.success("✅ Logged in.")
                st.rerun()
            else:
                st.error("❌ Invalid API Key.")
        st.markdown("Don't have one? [Get your Perplexity API Key](https://www.perplexity.ai)")
        return

    page = st.sidebar.radio("Navigate", ["🤖 Chatbot", "📄 Instructions", "⚙️ Settings"])
    if page == "🤖 Chatbot":
        display_chat()
    elif page == "📄 Instructions":
        instructions_page()
    elif page == "⚙️ Settings":
        settings_page()

if __name__ == "__main__":
    main()
