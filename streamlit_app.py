import streamlit as st
import google.generativeai as genai
import requests
import sqlite3
import uuid
import time
from datetime import datetime

# DB Setup
DB_NAME = "chatbot_v4.db"

def get_db_connection():
    # Adding timeout and check_same_thread=False prevents "database is locked" errors in Streamlit
    return sqlite3.connect(DB_NAME, timeout=15, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, client_id TEXT, title TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_sessions(client_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, title FROM sessions WHERE client_id = ? ORDER BY created_at DESC', (client_id,))
    sessions = c.fetchall()
    conn.close()
    return sessions

def create_session(client_id, title="New Chat"):
    session_id = str(uuid.uuid4())
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO sessions (id, client_id, title) VALUES (?, ?, ?)', (session_id, client_id, title))
    conn.commit()
    conn.close()
    return session_id

def get_messages(session_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC', (session_id,))
    messages = [{"role": row[0], "content": row[1]} for row in c.fetchall()]
    conn.close()
    return messages

def save_message(session_id, role, content):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)', (session_id, role, content))
    conn.commit()
    conn.close()

def update_session_title(session_id, title):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE sessions SET title = ? WHERE id = ?', (title, session_id))
    conn.commit()
    conn.close()

init_db()

# State Management
if "client_id" not in st.session_state:
    st.session_state.client_id = str(uuid.uuid4())
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "current_session" not in st.session_state:
    sessions = get_sessions(st.session_state.client_id)
    if sessions:
        st.session_state.current_session = sessions[0][0]
    else:
        st.session_state.current_session = create_session(st.session_state.client_id)

# Set page config
st.set_page_config(page_title="ShaiksGPT", page_icon="🤖", layout="wide")

# Theme logic
if st.session_state.theme == "dark":
    bg_color = "#212121"
    sidebar_bg = "#171717"
    text_color = "#FFFFFF"
    input_bg = "#2f2f2f"
else:
    bg_color = "#FFFFFF"
    sidebar_bg = "#F7F7F8"
    text_color = "#000000"
    input_bg = "#FFFFFF"

# Custom CSS
st.markdown(f"""
<style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
        transition: all 0.3s ease-in-out;
    }}
    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg};
        transition: all 0.3s ease-in-out;
    }}
    .stChatInputContainer {{
        background-color: {input_bg} !important;
        border-radius: 20px !important;
        border: 1px solid #4a4a4a !important;
        transition: all 0.3s ease-in-out;
    }}
    .stChatInputContainer textarea {{
        color: {text_color} !important;
    }}
    .disclaimer {{
        text-align: center;
        font-size: 12px;
        color: #aaaaaa;
        margin-top: 10px;
    }}
    
    /* Animations */
    .stChatMessage {{
        animation: fadeIn 0.5s ease-in-out;
    }}
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
</style>
""", unsafe_allow_html=True)

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Sidebar
with st.sidebar:
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"<h3 style='color: {text_color}; margin: 0;'>🤖 ShaiksGPT</h3>", unsafe_allow_html=True)
    with col2:
        if st.button("📝", help="New Chat"):
            st.session_state.current_session = create_session(st.session_state.client_id)
            st.rerun()
            
    st.markdown("---")
    
    # List sessions from DB
    sessions = get_sessions(st.session_state.client_id)
    
    # Add a scrollable container for history
    st.markdown('<div style="height: 50vh; overflow-y: auto;">', unsafe_allow_html=True)
    for s_id, s_title in sessions:
        btn_label = f"💬 {s_title}"
        if s_id == st.session_state.current_session:
            btn_label = f"**{btn_label}**"
        
        if st.button(btn_label, key=s_id, use_container_width=True):
            st.session_state.current_session = s_id
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>"*5, unsafe_allow_html=True)
    
    col3, col4 = st.columns(2)
    with col3:
        theme_icon = "🌞" if st.session_state.theme == "dark" else "🌙"
        if st.button(theme_icon, use_container_width=True, help="Toggle Theme"):
            st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
            st.rerun()
    with col4:
        st.button("⚙️", use_container_width=True, key="settings_btn", help="Settings")

# Main Chat Area
messages = get_messages(st.session_state.current_session)

if not messages:
    with st.chat_message("assistant", avatar="🤖"):
        st.write("Hello! How can I assist you today?")

# Display existing history
for msg in messages:
    with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else None):
        st.write(msg["content"])

# Helper function for typing indicator
def stream_response(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.03)

if user_input := st.chat_input("Message ShaiksGPT..."):
    # First message determines the title
    if not messages:
        title = user_input[:20] + "..." if len(user_input) > 20 else user_input
        update_session_title(st.session_state.current_session, title)
        
    save_message(st.session_state.current_session, "user", user_input)
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant", avatar="🤖"):
        try:
            with st.spinner("Searching the web for live answers..."):
                serp_api_url = "https://serpapi.com/search.json"
                params = {
                    "q": user_input,
                    "api_key": "740311d2537c68d3d76de33de8c68a5e0a64108176c0c5742107c17bfaf697a3"
                }
                search_response = requests.get(serp_api_url, params=params)
                
                search_context = ""
                if search_response.status_code == 200:
                    results = search_response.json()
                    snippets = []
                    if "organic_results" in results:
                        for result in results["organic_results"][:3]:
                            if "snippet" in result:
                                snippets.append(result["snippet"])
                    if snippets:
                        search_context = "Live search results:\n" + "\n".join(snippets) + "\n\n"
                
                prompt = search_context + f"Question: {user_input}\nPlease provide a helpful answer. Use the live search results above if they are relevant."
            
            # Same core logic
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            
            # Typing effect
            st.write_stream(stream_response(response.text))
            
            save_message(st.session_state.current_session, "assistant", response.text)

        except Exception as e:
            st.error(str(e))

st.markdown('<div class="disclaimer">ShaiksGPT can make mistakes. Consider verifying important information.</div>', unsafe_allow_html=True)
