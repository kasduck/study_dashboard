import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from icalendar import Calendar, Event
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from onesignal_sdk.client import Client as OneSignalClient
from firebase_admin import credentials, initialize_app, auth, firestore
import random
import re

# Initialize Firebase
try:
    _ = firestore.client()
except ValueError:
    try:
        firebase_json = st.secrets["firebase"]["FIREBASE_SERVICE_ACCOUNT_JSON"].strip()
        if firebase_json.startswith('"""') and firebase_json.endswith('"""'):
            firebase_json = firebase_json[3:-3].strip()
        if firebase_json.startswith("'") and firebase_json.endswith("'"):
            firebase_json = firebase_json[1:-1].strip()
        firebase_json = re.sub(r'^\s+|\s+$', '', firebase_json)
        cred = credentials.Certificate(json.loads(firebase_json))
        initialize_app(cred, {'projectId': st.secrets["firebase"]["FIREBASE_PROJECT_ID"]})
    except KeyError as e:
        st.error(f"Missing secret: {e}. Check your secrets.toml or Streamlit Cloud secrets.")
        st.stop()
    except Exception as e:
        st.error(f"Could not parse FIREBASE_SERVICE_ACCOUNT_JSON: {e}")
        st.stop()

db = firestore.client()

# Page Configuration
st.set_page_config(
    page_title="Study Progress Dashboard",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS with improved readability, gradients, and animations
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Root Variables for Better Theming */
    :root {
        --primary-bg: #0f0f23;
        --secondary-bg: #1a1a2e;
        --accent-bg: #16213e;
        --card-bg: rgba(26, 26, 46, 0.8);
        --glass-bg: rgba(255, 255, 255, 0.05);
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --success-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        --warning-gradient: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        --text-primary: #ffffff;
        --text-secondary: #b3b3b3;
        --text-muted: #666666;
        --border-color: rgba(255, 255, 255, 0.1);
        --shadow-light: 0 8px 32px rgba(0, 0, 0, 0.3);
        --shadow-medium: 0 12px 48px rgba(0, 0, 0, 0.4);
        --shadow-heavy: 0 20px 64px rgba(0, 0, 0, 0.5);
        --border-radius: 16px;
        --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Base Styling */
    * {
        box-sizing: border-box;
    }

    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: var(--primary-bg);
        background-image: 
            radial-gradient(circle at 25% 25%, rgba(102, 126, 234, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 75% 75%, rgba(245, 87, 108, 0.1) 0%, transparent 50%);
        color: var(--text-primary);
        line-height: 1.6;
        overflow-x: hidden;
    }

    /* Scrollbar Styling */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--secondary-bg);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--primary-gradient);
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--secondary-gradient);
    }

    /* Sidebar Styling */
    .sidebar .sidebar-content {
        background: var(--card-bg);
        backdrop-filter: blur(20px);
        border-right: 1px solid var(--border-color);
        border-radius: 0 var(--border-radius) var(--border-radius) 0;
        padding: 2rem 1.5rem;
        box-shadow: var(--shadow-medium);
        position: relative;
        overflow: hidden;
    }

    .sidebar .sidebar-content::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: var(--primary-gradient);
        border-radius: var(--border-radius) var(--border-radius) 0 0;
    }

    /* Main Container */
    .main-container {
        background: var(--card-bg);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-color);
        border-radius: var(--border-radius);
        padding: 2.5rem;
        margin: 1.5rem;
        box-shadow: var(--shadow-medium);
        position: relative;
        overflow: hidden;
        transition: var(--transition);
    }

    .main-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        z-index: -1;
    }

    .main-container:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-heavy);
        border-color: rgba(255, 255, 255, 0.2);
    }

    /* Header Styling */
    .main-header {
        background: var(--primary-gradient);
        color: var(--text-primary);
        padding: 3rem 2.5rem;
        border-radius: var(--border-radius);
        margin-bottom: 2rem;
        text-align: center;
        position: relative;
        overflow: hidden;
        box-shadow: var(--shadow-light);
    }

    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(45deg, transparent 30%, rgba(255, 255, 255, 0.1) 50%, transparent 70%);
        animation: shine 3s ease-in-out infinite;
    }

    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }

    .main-header p {
        font-size: 1.2rem;
        opacity: 0.9;
        margin: 0.5rem 0 0 0;
        font-weight: 400;
    }

    /* Stats Cards */
    .stats-card {
        background: var(--card-bg);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-color);
        border-radius: var(--border-radius);
        padding: 2rem;
        margin: 0.75rem;
        text-align: center;
        position: relative;
        overflow: hidden;
        transition: var(--transition);
        cursor: pointer;
    }

    .stats-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--success-gradient);
        border-radius: var(--border-radius) var(--border-radius) 0 0;
    }

    .stats-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: var(--shadow-heavy);
        border-color: rgba(255, 255, 255, 0.3);
    }

    .stats-card:hover::before {
        background: var(--primary-gradient);
    }

    .stats-card h3 {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-secondary);
        margin: 0 0 1rem 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .stats-card h2 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .stats-card p {
        font-size: 0.9rem;
        color: var(--text-muted);
        margin: 0.5rem 0 0 0;
    }

    /* Progress Cards */
    .progress-card {
        background: var(--card-bg);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-color);
        border-left: 4px solid transparent;
        border-image: var(--success-gradient) 1;
        border-radius: var(--border-radius);
        padding: 2rem;
        margin: 0.75rem;
        position: relative;
        overflow: hidden;
        transition: var(--transition);
    }

    .progress-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: var(--success-gradient);
        border-radius: var(--border-radius) 0 0 var(--border-radius);
    }

    .progress-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-medium);
    }

    /* Badge Cards */
    .badge-card {
        background: var(--card-bg);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-color);
        border-radius: var(--border-radius);
        padding: 2rem 1.5rem;
        margin: 0.75rem;
        text-align: center;
        position: relative;
        overflow: hidden;
        transition: var(--transition);
        cursor: pointer;
    }

    .badge-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: var(--warning-gradient);
        opacity: 0;
        transition: var(--transition);
    }

    .badge-card:hover {
        transform: translateY(-6px) scale(1.05);
        box-shadow: var(--shadow-heavy);
    }

    .badge-card:hover::before {
        opacity: 0.1;
    }

    .badge-card h2 {
        font-size: 2.5rem;
        margin: 0 0 1rem 0;
        filter: drop-shadow(0 0 10px currentColor);
    }

    .badge-card h4 {
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0;
        color: var(--text-primary);
    }

    /* Item States */
    .locked-item {
        background: var(--card-bg);
        backdrop-filter: blur(10px);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        opacity: 0.6;
        transition: var(--transition);
        position: relative;
    }

    .locked-item::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: repeating-linear-gradient(
            45deg,
            transparent,
            transparent 10px,
            rgba(255, 255, 255, 0.02) 10px,
            rgba(255, 255, 255, 0.02) 20px
        );
        pointer-events: none;
    }

    .completed-item {
        background: linear-gradient(135deg, rgba(79, 172, 254, 0.2) 0%, rgba(0, 242, 254, 0.2) 100%);
        border: 1px solid rgba(79, 172, 254, 0.3);
        border-left: 4px solid #4facfe;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        position: relative;
        overflow: hidden;
        animation: slideInFromLeft 0.5s ease-out;
    }

    .completed-item::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
        animation: sweep 2s ease-in-out infinite;
    }

    .next-item {
        background: linear-gradient(135deg, rgba(250, 112, 154, 0.2) 0%, rgba(254, 225, 64, 0.2) 100%);
        border: 1px solid rgba(250, 112, 154, 0.3);
        border-left: 4px solid #fa709a;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        position: relative;
        overflow: hidden;
        animation: pulse 2s ease-in-out infinite;
    }

    .next-item::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
        animation: glow 2s ease-in-out infinite;
    }

    /* Motivational Quote */
    .motivational-quote {
        background: var(--card-bg);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-color);
        border-radius: var(--border-radius);
        padding: 2.5rem;
        margin: 2rem 0;
        text-align: center;
        position: relative;
        overflow: hidden;
    }

    .motivational-quote::before {
        content: '"';
        position: absolute;
        top: 1rem;
        left: 2rem;
        font-size: 4rem;
        color: var(--text-muted);
        font-family: 'Georgia', serif;
    }

    .motivational-quote::after {
        content: '"';
        position: absolute;
        bottom: 1rem;
        right: 2rem;
        font-size: 4rem;
        color: var(--text-muted);
        font-family: 'Georgia', serif;
    }

    /* Tooltips */
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }

    .tooltip .tooltiptext {
        visibility: hidden;
        background: var(--card-bg);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-color);
        color: var(--text-primary);
        text-align: center;
        border-radius: 8px;
        padding: 12px 16px;
        position: absolute;
        z-index: 1000;
        bottom: 150%;
        left: 50%;
        transform: translateX(-50%) translateY(10px);
        opacity: 0;
        transition: var(--transition);
        white-space: nowrap;
        font-size: 0.875rem;
        box-shadow: var(--shadow-light);
    }

    .tooltip .tooltiptext::after {
        content: '';
        position: absolute;
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        border: 6px solid transparent;
        border-top-color: var(--border-color);
    }

    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
        transform: translateX(-50%) translateY(0);
    }

    /* Message Boxes */
    .message-box {
        background: var(--card-bg);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(79, 172, 254, 0.3);
        border-left: 4px solid #4facfe;
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
        position: relative;
        overflow: hidden;
        animation: slideInFromRight 0.5s ease-out;
    }

    .message-box.warning {
        border-color: rgba(250, 112, 154, 0.3);
        border-left-color: #fa709a;
        background: linear-gradient(135deg, rgba(250, 112, 154, 0.1) 0%, rgba(254, 225, 64, 0.1) 100%);
    }

    .completion-message {
        font-size: 1.1rem;
        font-weight: 500;
        margin: 0.75rem 0;
        animation: fadeInUp 0.7s ease-out;
    }

    /* Buttons */
    .stButton>button {
        background: var(--primary-gradient) !important;
        color: var(--text-primary) !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: var(--transition) !important;
        position: relative !important;
        overflow: hidden !important;
        box-shadow: var(--shadow-light) !important;
    }

    .stButton>button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        transition: left 0.5s ease;
    }

    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-heavy) !important;
    }

    .stButton>button:hover::before {
        left: 100%;
    }

    .stButton>button:active {
        transform: translateY(0) !important;
    }

    /* Form Inputs */
    .stTextInput>div>input,
    .stTimeInput>div>input,
    .stSelectbox>div>select,
    .stMultiselect>div>select {
        background: var(--card-bg) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        padding: 0.75rem 1rem !important;
        color: var(--text-primary) !important;
        font-size: 1rem !important;
        transition: var(--transition) !important;
    }

    .stTextInput>div>input:focus,
    .stTimeInput>div>input:focus,
    .stSelectbox>div>select:focus,
    .stMultiselect>div>select:focus {
        border-color: rgba(102, 126, 234, 0.5) !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2) !important;
        outline: none !important;
    }

    /* Expanders */
    .stExpander {
        background: var(--card-bg) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--border-radius) !important;
        margin-bottom: 1.5rem !important;
        overflow: hidden !important;
        transition: var(--transition) !important;
    }

    .stExpander:hover {
        border-color: rgba(255, 255, 255, 0.2) !important;
        box-shadow: var(--shadow-light) !important;
    }

    .stExpander > div > div {
        background: var(--card-bg) !important;
        backdrop-filter: blur(20px) !important;
    }

    /* Charts */
    .stPlotlyChart {
        background: var(--card-bg) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--border-radius) !important;
        padding: 1.5rem !important;
        margin: 1rem 0 !important;
        transition: var(--transition) !important;
    }

    .stPlotlyChart:hover {
        transform: translateY(-3px) !important;
        box-shadow: var(--shadow-medium) !important;
    }

    /* DataFrames */
    .stDataFrame {
        background: var(--card-bg) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--border-radius) !important;
        overflow: hidden !important;
        box-shadow: var(--shadow-light) !important;
    }

    /* Metrics */
    .stMetric {
        background: var(--card-bg) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        margin: 1rem 0 !important;
        transition: var(--transition) !important;
    }

    .stMetric:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-light) !important;
    }

    /* Animations */
    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.02); opacity: 0.9; }
    }

    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes slideInFromLeft {
        from {
            opacity: 0;
            transform: translateX(-30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes slideInFromRight {
        from {
            opacity: 0;
            transform: translateX(30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes shine {
        0% { transform: translateX(-100%) rotate(45deg); }
        100% { transform: translateX(100%) rotate(45deg); }
    }

    @keyframes sweep {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }

    @keyframes glow {
        0%, 100% { opacity: 0.5; }
        50% { opacity: 1; }
    }

    /* Responsive Design */
    @media (max-width: 768px) {
        .main-container {
            margin: 0.5rem;
            padding: 1.5rem;
        }
        
        .main-header {
            padding: 2rem 1.5rem;
        }
        
        .main-header h1 {
            font-size: 2rem;
        }
        
        .stats-card {
            margin: 0.5rem 0;
        }
        
        .stats-card h2 {
            font-size: 2rem;
        }
    }

    /* Loading States */
    .loading {
        animation: pulse 2s ease-in-out infinite;
    }

    /* Focus States for Accessibility */
    *:focus {
        outline: 2px solid rgba(102, 126, 234, 0.5);
        outline-offset: 2px;
    }

    /* Custom Selection */
    ::selection {
        background: rgba(102, 126, 234, 0.3);
        color: var(--text-primary);
    }

    /* High Contrast Mode Support */
    @media (prefers-contrast: high) {
        :root {
            --border-color: rgba(255, 255, 255, 0.3);
            --text-secondary: #e0e0e0;
        }
    }

    /* Reduced Motion Support */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.curriculum_data = None
    st.session_state.curriculum_file = None
    st.session_state.progress_data = {}
    st.session_state.study_hours = 0
    st.session_state.streak_counter = 0
    st.session_state.badges = []
    st.session_state.last_study_date = None
    st.session_state.dark_mode = False
    st.session_state.notifications_enabled = True
    st.session_state.user_email = ""
    st.session_state.schedule_data = []
    st.session_state.user_id = None
    st.session_state.authenticated = False
    st.session_state.reset_confirmed = False
    st.session_state.completion_messages = {}

# Motivational quotes
MOTIVATIONAL_QUOTES = [
    "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
    "The only way to do great work is to love what you do. - Steve Jobs",
    "Don't watch the clock; do what it does. Keep going. - Sam Levenson",
    "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
    "It is during our darkest moments that we must focus to see the light. - Aristotle",
    "Believe you can and you're halfway there. - Theodore Roosevelt",
    "If you know the enemy and know yourself, you need not fear the result of a hundred battles. - Sun Tzu",
    "The only limit to our realization of tomorrow will be our doubts of today. - Franklin D. Roosevelt",
    "Act as if what you do makes a difference. It does. - William James",
    "Success usually comes to those who are too busy to be looking for it. - Henry David Thoreau",
    "You miss 100 percent of the shots you don't take. - Wayne Gretzky",
    "The best way to predict the future is to create it. - Peter Drucker",
    "Your time is limited, don't waste it living someone else's life. - Steve Jobs",
    "The only impossible journey is the one you never begin. - Tony Robbins",
    "Success is walking from failure to failure with no loss of enthusiasm. - Winston Churchill",
    "The road to success and the road to failure are almost exactly the same. - Colin R. Davis",
    "What lies behind us and what lies before us are tiny matters compared to what lies within us. - Ralph Waldo Emerson",
    "The only way to achieve the impossible is to believe it is possible. - Charles Kingsleigh",
    "Dream big and dare to fail. - Norman Vaughan",
    "The only limit to our realization of tomorrow is our doubts of today. - Franklin D. Roosevelt",
    "Success is not how high you have climbed, but how you make a positive difference to the world. - Roy T. Bennett",
]

def get_motivational_quote():
    return random.choice(MOTIVATIONAL_QUOTES)

def load_curriculum_data():
    if 'curriculum_file' not in st.session_state or st.session_state.curriculum_file is None:
        st.warning("Please upload a curriculum CSV file to populate the checklist.")
        return {}
    
    try:
        df = pd.read_csv(st.session_state.curriculum_file)
        curriculum_data = {}
        for (module, chapter), group in df.groupby(['Module', 'Chapter']):
            subtopics = group['Subtopic'].tolist()
            project = group['Project'].iloc[0] if not group['Project'].empty else ""
            if module not in curriculum_data:
                curriculum_data[module] = {}
            curriculum_data[module][chapter] = {
                'subtopics': subtopics,
                'project': project
            }
        return curriculum_data
    except Exception as e:
        st.error(f"Error loading curriculum data: {str(e)}")
        return {}

# Authentication functions
def sign_in(email, password):
    try:
        user = auth.get_user_by_email(email)
        st.session_state.user_id = user.uid
        st.session_state.user_email = email
        st.session_state.authenticated = True
        sync_user_data(user.uid)
        st.success("Signed in successfully!")
    except auth.AuthError as e:
        st.error(f"Sign-in error: {str(e)}")
    except Exception as e:
        st.error(f"Unexpected sign-in error: {str(e)}")

def sign_up(email, password):
    try:
        user = auth.create_user(email=email, password=password)
        st.session_state.user_id = user.uid
        st.session_state.user_email = email
        st.session_state.authenticated = True
        db.collection('users').document(user.uid).set({'email': email})
        sync_user_data(user.uid)
        st.success("Signed up successfully!")
    except auth.AuthError as e:
        st.error(f"Sign-up error: {str(e.detail)}")
    except Exception as e:
        st.error(f"Unexpected sign-up error: {str(e)}")

def sign_out():
    st.session_state.user_id = None
    st.session_state.user_email = ""
    st.session_state.authenticated = False
    st.session_state.progress_data = {}
    st.session_state.badges = []
    st.session_state.study_hours = 0
    st.session_state.streak_counter = 0
    st.session_state.schedule_data = []
    st.success("Signed out successfully!")

def sync_user_data(user_id):
    try:
        progress_ref = db.collection('progress').where(
            filter=firestore.FieldFilter('user_id', '==', user_id)
        ).where(
            filter=firestore.FieldFilter('completed', '==', True)
        )
        docs = progress_ref.stream()
        for doc in docs:
            data = doc.to_dict()
            key = f"{data['module']}_{data['chapter']}_{data['subtopic']}"
            st.session_state.progress_data[key] = data['completed']
        
        badges_ref = db.collection('badges').where(
            filter=firestore.FieldFilter('user_id', '==', user_id)
        )
        docs = badges_ref.stream()
        st.session_state.badges = [doc.to_dict()['badge_name'] for doc in docs]
        
        sessions_ref = db.collection('study_sessions').where(
            filter=firestore.FieldFilter('user_id', '==', user_id)
        )
        docs = sessions_ref.stream()
        st.session_state.study_hours = sum(doc.to_dict().get('Hours', 0) for doc in docs)
        st.session_state.streak_counter = len(list(docs)) if docs else 0
    except Exception as e:
        st.error(f"Error syncing data from Firestore: {str(e)}")

def save_progress_to_supabase(user_id, module, chapter, subtopic, completed):
    try:
        doc_id = f"{user_id}_{module}_{chapter}_{subtopic}".replace(" ", "_")
        doc_ref = db.collection('progress').document(doc_id)
        doc_ref.set({
            'user_id': user_id,
            'module': module,
            'chapter': chapter,
            'subtopic': subtopic,
            'completed': completed,
            'completed_at': firestore.SERVER_TIMESTAMP if completed else None,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return True
    except Exception as e:
        st.error(f"Error saving progress to Firestore: {str(e)}")
        return False

def save_badge_to_supabase(user_id, badge_name):
    try:
        doc_ref = db.collection('badges').document(f"{user_id}_{badge_name}".replace(" ", "_"))
        doc_ref.set({
            'user_id': user_id,
            'badge_name': badge_name,
            'earned_at': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        st.error(f"Error saving badge to Firestore: {str(e)}")

def save_study_session_to_supabase(user_id, hours):
    try:
        doc_ref = db.collection('study_sessions').document(f"{user_id}_{datetime.now().date().isoformat()}")
        doc_ref.set({
            'user_id': user_id,
            'date': datetime.now().date().isoformat(),
            'hours': hours
        })
    except Exception as e:
        st.error(f"Error saving study session to Firestore: {str(e)}")

def send_email_notification(to_email, subject, content):
    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        message = Mail(
            from_email=os.getenv("FROM_EMAIL"),
            to_emails=to_email,
            subject=subject,
            html_content=content
        )
        response = sg.send(message)
        if response.status_code == 202:
            st.success("Email notification sent!")
        else:
            st.error(f"Failed to send email: {response.status_code} - {response.body.decode('utf-8')}")
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")

def send_push_notification(message):
    try:
        client = OneSignalClient(
            app_id=os.getenv("ONESIGNAL_APP_ID"),
            rest_api_key=os.getenv("ONESIGNAL_API_KEY")
        )
        notification_body = {
            "contents": {"en": message},
            "included_segments": ["All"]
        }
        response = client.send_notification(notification_body)
        if response.status_code == 200:
            st.success("Push notification sent!")
        else:
            st.error(f"Failed to send push notification: {response.status_code} - {response.body}")
    except Exception as e:
        st.error(f"Error sending push notification: {str(e)}")

def calculate_progress_stats(progress_data, curriculum_data):
    if not curriculum_data:
        return 0, 0, 0, 0
    
    total_subtopics = 0
    completed_subtopics = 0
    
    for module, chapters in curriculum_data.items():
        for chapter, content in chapters.items():
            total_subtopics += len(content.get('subtopics', []))
            for subtopic in content.get('subtopics', []):
                if progress_data.get(f"{module}_{chapter}_{subtopic}", False):
                    completed_subtopics += 1
    
    completion_percentage = (completed_subtopics / total_subtopics * 100) if total_subtopics > 0 else 0
    
    return completion_percentage, completed_subtopics, total_subtopics, len(curriculum_data)

def render_progress_dashboard():
    if not st.session_state.authenticated:
        st.warning("Please sign in to access the dashboard.")
        return
    
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    st.markdown('<div class="main-header"><h1>📚 Study Progress Dashboard</h1><p>Your learning journey, gamified and visualized!</p></div>', unsafe_allow_html=True)
    
    if st.session_state.curriculum_data is None:
        st.session_state.curriculum_data = load_curriculum_data()
    
    completion_percentage, completed_subtopics, total_subtopics, total_modules = calculate_progress_stats(
        st.session_state.progress_data, st.session_state.curriculum_data
    )
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stats-card">
            <h3>📊 Progress</h3>
            <h2>{completion_percentage:.1f}%</h2>
            <p>Overall Completion</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stats-card">
            <h3>✅ Completed</h3>
            <h2>{completed_subtopics}/{total_subtopics}</h2>
            <p>Subtopics Done</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stats-card">
            <h3>⏰ Study Hours</h3>
            <h2>{st.session_state.study_hours}</h2>
            <p>Hours Logged</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stats-card">
            <h3>🔥 Streak</h3>
            <h2>{st.session_state.streak_counter}</h2>
            <p>Days in a Row</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f'<div class="motivational-quote">💡 {get_motivational_quote()}</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        module_completion = []
        module_names = []
        
        for module, chapters in st.session_state.curriculum_data.items():
            total_module_subtopics = 0
            completed_module_subtopics = 0
            
            for chapter, content in chapters.items():
                total_module_subtopics += len(content.get('subtopics', []))
                for subtopic in content.get('subtopics', []):
                    if st.session_state.progress_data.get(f"{module}_{chapter}_{subtopic}", False):
                        completed_module_subtopics += 1
            
            completion_rate = (completed_module_subtopics / total_module_subtopics * 100) if total_module_subtopics > 0 else 0
            module_completion.append(completion_rate)
            module_names.append(module.split(":")[0])
        
        fig_pie = px.pie(
            values=module_completion,
            names=module_names,
            title="Module Completion Distribution",
            color_discrete_sequence=px.colors.qualitative.Set2,
            hover_data={'values': module_completion},
        )
        fig_pie.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Completion: %{value:.1f}%<extra></extra>',
            pull=[0.05] * len(module_names),
            marker=dict(line=dict(color='#ffffff', width=2))
        )
        fig_pie.update_layout(
            margin=dict(t=50, b=50, l=50, r=50),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=True,
            font=dict(size=14, family='Roboto', color='#1e293b'),
            hoverlabel=dict(bgcolor='#ffffff', font_size=12, font_family='Roboto')
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        hours = [15, 22, 18, 25]
        
        fig_bar = px.bar(
            x=weeks,
            y=hours,
            title="Weekly Study Hours",
            color=hours,
            color_continuous_scale="Viridis",
            text=hours,
        )
        fig_bar.update_traces(
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Hours: %{y}<extra></extra>',
            marker=dict(line=dict(color='#ffffff', width=2)),
            selector=dict(type='bar')
        )
        fig_bar.update_layout(
            margin=dict(t=50, b=50, l=50, r=50),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(size=14, family='Roboto', color='#1e293b'),
            hoverlabel=dict(bgcolor='#ffffff', font_size=12, font_family='Roboto'),
            xaxis_title="Week",
            yaxis_title="Hours",
            showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    st.subheader("📈 Completed Subtopics by Module")
    try:
        progress_ref = db.collection('progress').where(
            filter=firestore.FieldFilter('user_id', '==', st.session_state.user_id)
        ).where(
            filter=firestore.FieldFilter('completed', '==', True)
        )
        docs = progress_ref.stream()
        progress_data = [doc.to_dict() for doc in docs]
        module_counts = {}
        for entry in progress_data:
            module = entry['module'].split(":")[0]
            module_counts[module] = module_counts.get(module, 0) + 1
        
        if module_counts:
            modules = list(module_counts.keys())
            counts = list(module_counts.values())
            fig_subtopics = go.Figure(data=[
                go.Bar(
                    x=modules,
                    y=counts,
                    marker_color='#22d3ee',
                    text=counts,
                    textposition='outside',
                    hovertemplate='<b>%{x}</b><br>Completed: %{y}<extra></extra>',
                    marker=dict(line=dict(color='#ffffff', width=2))
                )
            ])
            fig_subtopics.update_layout(
                title="Completed Subtopics by Module",
                xaxis_title="Module",
                yaxis_title="Completed Subtopics",
                template="plotly_white",
                margin=dict(t=50, b=50, l=50, r=50),
                font=dict(size=14, family='Roboto', color='#1e293b'),
                hoverlabel=dict(bgcolor='#ffffff', font_size=12, font_family='Roboto')
            )
            st.plotly_chart(fig_subtopics, use_container_width=True)
        else:
            st.info("No completed subtopics yet. Mark some in the Checklist to see the chart!")
    except Exception as e:
        st.error(f"Error fetching progress from Firestore: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_curriculum_checklist():
    if not st.session_state.authenticated:
        st.warning("Please sign in to access the checklist.")
        return
    
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    st.header("📋 Curriculum Checklist")
    
    if st.session_state.curriculum_data is None or st.session_state.curriculum_file is None:
        file_obj = download_curriculum_from_firestore(st.session_state.user_id)
        if file_obj:
            st.session_state.curriculum_file = file_obj
            st.session_state.curriculum_data = load_curriculum_data()
        if st.session_state.curriculum_data is None or st.session_state.curriculum_file is None:
            uploaded_file = st.file_uploader("Upload Curriculum CSV", type=["csv"], help="Upload a CSV file containing your curriculum data.")
            if uploaded_file is not None:
                upload_curriculum_to_firestore(st.session_state.user_id, uploaded_file)
                file_obj = download_curriculum_from_firestore(st.session_state.user_id)
                if file_obj:
                    st.session_state.curriculum_file = file_obj
                    st.session_state.curriculum_data = load_curriculum_data()
                    st.rerun()
            else:
                st.warning("Please upload a curriculum CSV file to populate the checklist.")
                return
    
    if 'completion_messages' not in st.session_state:
        st.session_state.completion_messages = {}
    
    search_term = st.text_input("🔍 Search subtopics...", placeholder="Search for subtopics...", key="search_subtopics")
    
    for module, chapters in st.session_state.curriculum_data.items():
        with st.expander(f"📚 {module}", expanded=True):
            for chapter, content in chapters.items():
                st.subheader(f"📖 {chapter}")
                
                for i, subtopic in enumerate(content.get('subtopics', [])):
                    if search_term.lower() in subtopic.lower() or not search_term:
                        key = f"{module}_{chapter}_{subtopic}"
                        is_unlocked = i == 0 or (i > 0 and st.session_state.progress_data.get(
                            f"{module}_{chapter}_{content.get('subtopics', [])[i-1]}", False))
                        is_completed = st.session_state.progress_data.get(key, False)
                        
                        col1, col2, col3 = st.columns([1, 8, 1])
                        
                        with col1:
                            if is_unlocked:
                                new_value = st.checkbox(" ", key=f"checkbox_{key}", value=is_completed)
                                if new_value != is_completed:
                                    if save_progress_to_supabase(st.session_state.user_id, module, chapter, subtopic, new_value):
                                        st.session_state.progress_data[key] = new_value
                                        if new_value:
                                            st.session_state.study_hours += 2
                                            check_and_award_badges()
                                            st.session_state.completion_messages[key] = f"🎉 Subtopic '{subtopic}' completed!"
                                        else:
                                            st.session_state.study_hours = max(0, st.session_state.study_hours - 2)
                                            st.session_state.completion_messages[key] = f"Subtopic '{subtopic}' marked incomplete."
                                        st.rerun()
                            else:
                                st.markdown('<div class="tooltip">🔒<span class="tooltiptext">Complete previous subtopic</span></div>', unsafe_allow_html=True)
                        
                        with col2:
                            if is_completed:
                                st.markdown(f'<div class="completed-item">✅ {subtopic}</div>', unsafe_allow_html=True)
                            elif is_unlocked:
                                st.markdown(f'<div class="next-item">⏳ {subtopic}</div>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<div class="locked-item">🔒 {subtopic}</div>', unsafe_allow_html=True)
                            if key in st.session_state.completion_messages:
                                st.markdown(
                                    f'<div class="message-box">{st.session_state.completion_messages[key]}</div>',
                                    unsafe_allow_html=True
                                )
                        
                        with col3:
                            if is_completed:
                                st.markdown("✅")
                            elif is_unlocked:
                                st.markdown("⏳")
                            else:
                                st.markdown('<div class="tooltip">🔒<span class="tooltiptext">Locked</span></div>', unsafe_allow_html=True)
                
                if 'project' in content:
                    if st.button(f"📋 View Project Details", key=f"project_{module}_{chapter}"):
                        st.info(f"**Project:** {content['project']}")
    
    st.session_state.completion_messages = {}
    st.markdown('</div>', unsafe_allow_html=True)

def check_and_award_badges():
    if not st.session_state.authenticated:
        return
    
    completion_percentage, completed_subtopics, total_subtopics, total_modules = calculate_progress_stats(
        st.session_state.progress_data, st.session_state.curriculum_data
    )
    
    badges_to_award = []
    
    if completed_subtopics >= 5 and "First Steps" not in st.session_state.badges:
        badges_to_award.append("First Steps")
    if completed_subtopics >= 10 and "Getting Started" not in st.session_state.badges:
        badges_to_award.append("Getting Started")
    if completion_percentage >= 25 and "Quarter Master" not in st.session_state.badges:
        badges_to_award.append("Quarter Master")
    if completion_percentage >= 50 and "Halfway Hero" not in st.session_state.badges:
        badges_to_award.append("Halfway Hero")
    if st.session_state.streak_counter >= 5 and "Streak Star" not in st.session_state.badges:
        badges_to_award.append("Streak Star")
    if st.session_state.study_hours >= 50 and "Study Master" not in st.session_state.badges:
        badges_to_award.append("Study Master")
    
    for badge in badges_to_award:
        st.session_state.badges.append(badge)
        save_badge_to_supabase(st.session_state.user_id, badge)
        st.balloons()
        st.success(f"🏆 Badge Earned: {badge}!")
        if st.session_state.notifications_enabled and st.session_state.user_email:
            send_email_notification(
                st.session_state.user_email,
                f"New Badge Earned: {badge}",
                f"Congratulations! You've earned the {badge} badge!"
            )
            send_push_notification(f"New Badge Earned: {badge}")

def render_trophy_case():
    if not st.session_state.authenticated:
        st.warning("Please sign in to view your trophy case.")
        return
    
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    st.header("🏆 Trophy Case")
    
    if not st.session_state.badges:
        st.info("Complete subtopics to earn badges!")
        return
    
    cols = st.columns(4)
    badge_icons = {
        "First Steps": "🚀",
        "Getting Started": "⭐",
        "Quarter Master": "🎯",
        "Halfway Hero": "🦸",
        "Streak Star": "🔥",
        "Study Master": "📚",
        "Module Master": "🎓"
    }
    
    for i, badge in enumerate(st.session_state.badges):
        col = cols[i % 4]
        with col:
            icon = badge_icons.get(badge, "🏆")
            st.markdown(f"""
            <div class="badge-card">
                <h2>{icon}</h2>
                <h4>{badge}</h4>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("Confirm Reset", width="small")
def reset_dialog():
    st.write("Are you sure you want to reset all progress?")
    if st.button("Yes, Reset All Progress"):
        reset_progress_data()
        st.rerun()

def render_study_schedule():
    if not st.session_state.authenticated:
        st.warning("Please sign in to access the schedule.")
        return
    
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    st.header("📅 Study Schedule")
    
    st.subheader("⚙️ Schedule Settings")
    col1, col2 = st.columns(2)
    
    with col1:
        daily_hours = st.slider("Daily Study Hours", 2, 8, 4, help="Set your daily study duration.")
        start_time = st.time_input("Preferred Start Time", value=datetime.strptime("09:00", "%H:%M").time(), help="Choose when to start studying.")
    
    with col2:
        study_days = st.multiselect(
            "Available Days",
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            default=["Monday", "Saturday", "Sunday"],
            help="Select days you're available to study."
        )
    
    if st.button("🗓️ Generate Schedule"):
        generate_study_schedule(daily_hours, start_time, study_days)
    
    if st.session_state.schedule_data:
        st.subheader("📋 Current Schedule")
        schedule_df = pd.DataFrame(st.session_state.schedule_data)
        st.dataframe(schedule_df, use_container_width=True)
        
        weekly_hours = st.session_state.study_hours % 7
        target_hours = 25
        fig_goal = go.Figure(data=[go.Indicator(
            value=weekly_hours,
            mode="gauge+number+delta",
            title={'text': "Weekly Hours Progress"},
            delta={'reference': target_hours},
            gauge={
                'axis': {'range': [0, 30]},
                'bar': {'color': "#22d3ee"},
                'steps': [
                    {'range': [0, 15], 'color': "#fef3c7"},
                    {'range': [15, 25], 'color': "#a7f3d0"},
                    {'range': [25, 30], 'color': "#6ee7b7"}
                ],
                'threshold': {
                    'line': {'color': "#1e293b", 'width': 4},
                    'thickness': 0.75,
                    'value': target_hours
                }
            }
        )])
        fig_goal.update_layout(
            margin=dict(t=50, b=50, l=50, r=50),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(size=14, family='Roboto', color='#1e293b'),
            hoverlabel=dict(bgcolor='#ffffff', font_size=12, font_family='Roboto')
        )
        st.plotly_chart(fig_goal, use_container_width=True)
        
        if st.button("📄 Export to Calendar (.ics)"):
            export_to_calendar()
    
    st.markdown('</div>', unsafe_allow_html=True)

def generate_study_schedule(daily_hours, start_time, study_days):
    st.session_state.schedule_data = []
    uncompleted_subtopics = []
    if not st.session_state.curriculum_data:
        st.session_state.curriculum_data = load_curriculum_data()
    for module, chapters in st.session_state.curriculum_data.items():
        for chapter, content in chapters.items():
            for subtopic in content.get('subtopics', []):
                key = f"{module}_{chapter}_{subtopic}"
                if not st.session_state.progress_data.get(key, False):
                    uncompleted_subtopics.append({
                        'module': module,
                        'chapter': chapter,
                        'subtopic': subtopic,
                        'estimated_hours': 2,
                        'deadline': content.get('deadline', '9999-12-31')
                    })
    
    uncompleted_subtopics.sort(key=lambda x: x['deadline'])
    
    current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = current_date + timedelta(days=14)
    scheduled_hours = 0
    target_weekly_hours = 25
    
    while current_date <= end_date and uncompleted_subtopics and scheduled_hours < target_weekly_hours:
        day_name = current_date.strftime("%A")
        if day_name in study_days:
            is_restricted = day_name in ["Tuesday", "Wednesday", "Thursday", "Friday"] and start_time.hour >= 12 and start_time.hour < 20
            if not is_restricted:
                session_duration = min(daily_hours, 3)
                if uncompleted_subtopics:
                    subtopic_data = uncompleted_subtopics.pop(0)
                    days_until_deadline = (datetime.strptime(subtopic_data['deadline'], "%Y-%m-%d").date() - current_date.date()).days
                    is_urgent = days_until_deadline <= 7
                    schedule_entry = {
                        'Date': current_date.strftime("%Y-%m-%d"),
                        'Day': day_name,
                        'Time': f"{start_time.hour:02d}:{start_time.minute:02d}",
                        'Duration': f"{session_duration}h",
                        'Module': subtopic_data['module'].split(":")[0],
                        'Chapter': subtopic_data['chapter'].split(":")[1] if ":" in subtopic_data['chapter'] else subtopic_data['chapter'],
                        'Subtopic': subtopic_data['subtopic'][:50] + "..." if len(subtopic_data['subtopic']) > 50 else subtopic_data['subtopic'],
                        'Urgent': is_urgent
                    }
                    st.session_state.schedule_data.append(schedule_entry)
                    scheduled_hours += session_duration
        current_date += timedelta(days=1)
    
    st.success(f"✅ Schedule generated for {len(st.session_state.schedule_data)} study sessions! (Target: {target_weekly_hours} hours/week)")

def export_to_calendar():
    cal = Calendar()
    cal.add('prodid', '-//Study Dashboard//mxm.dk//')
    cal.add('version', '2.0')
    
    for session in st.session_state.schedule_data:
        event = Event()
        event.add('summary', f"Study: {session['Subtopic']} {'(Urgent)' if session['Urgent'] else ''}")
        event.add('dtstart', datetime.strptime(f"{session['Date']} {session['Time']}", "%Y-%m-%d %H:%M"))
        event.add('dtend', datetime.strptime(f"{session['Date']} {session['Time']}", "%Y-%m-%d %H:%M") + timedelta(hours=int(session['Duration'].replace('h', ''))))
        event.add('description', f"Module: {session['Module']}\nChapter: {session['Chapter']}\nUrgent: {session['Urgent']}")
        cal.add_component(event)
    
    ics_content = cal.to_ical().decode('utf-8')
    st.download_button(
        label="📥 Download Calendar File",
        data=ics_content,
        file_name="study_schedule.ics",
        mime="text/calendar"
    )

def export_supabase_data():
    if not st.session_state.authenticated:
        st.warning("Please sign in to export data.")
        return
    
    try:
        progress_ref = db.collection('progress').where(
            filter=firestore.FieldFilter('user_id', '==', st.session_state.user_id)
        )
        docs = progress_ref.stream()
        progress_data = [doc.to_dict() for doc in docs]
        progress_df = pd.DataFrame(progress_data)
        progress_csv = progress_df.to_csv(index=False)
        
        badges_ref = db.collection('badges').where(
            filter=firestore.FieldFilter('user_id', '==', st.session_state.user_id)
        )
        docs = badges_ref.stream()
        badges_data = [doc.to_dict() for doc in docs]
        badges_df = pd.DataFrame(badges_data)
        badges_csv = badges_df.to_csv(index=False)
        
        st.download_button(
            label="Download Progress CSV",
            data=progress_csv,
            file_name="firestore_progress.csv",
            mime="text/csv"
        )
        st.download_button(
            label="Download Badges CSV",
            data=badges_csv,
            file_name="firestore_badges.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"Error exporting Firestore data: {str(e)}")

def render_settings():
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    st.header("⚙️ Settings")
    
    if not st.session_state.authenticated:
        st.subheader("👤 Sign In / Sign Up")
        with st.container():
            email = st.text_input("📧 Email", placeholder="Enter your email")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Sign In"):
                    sign_in(email, password)
            with col2:
                if st.button("Sign Up"):
                    sign_up(email, password)
    else:
        st.subheader("👤 User")
        st.write(f"Logged in as: {st.session_state.user_email}")
        if st.button("Sign Out"):
            sign_out()
    
    if st.session_state.authenticated:
        st.subheader("👤 User Preferences")
        col1, col2 = st.columns(2)
        
        with col1:
            st.session_state.user_email = st.text_input("📧 Email", value=st.session_state.user_email, disabled=True)
            st.session_state.dark_mode = st.checkbox("🌙 Dark Mode", value=st.session_state.dark_mode, help="Toggle dark mode (coming soon)")
        
        with col2:
            st.session_state.notifications_enabled = st.checkbox("🔔 Enable Notifications", value=st.session_state.notifications_enabled, help="Receive progress notifications")
            notification_frequency = st.selectbox("📅 Notification Frequency", ["Daily", "Weekly", "Monthly"], help="Choose how often to receive notifications")
        
        st.subheader("💾 Data Management")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📤 Export Progress"):
                export_progress_data()
        
        with col2:
            if st.button("🔄 Reset Progress"):
                reset_dialog()
        
        with col3:
            if st.button("📥 Export Firestore Data"):
                export_supabase_data()
    
    st.markdown('</div>', unsafe_allow_html=True)

def export_progress_data():
    if not st.session_state.authenticated:
        st.warning("Please sign in to export progress.")
        return
    
    progress_df = pd.DataFrame([
        {
            'Item': key,
            'Completed': value,
            'Timestamp': datetime.now().isoformat()
        }
        for key, value in st.session_state.progress_data.items()
    ])
    
    csv = progress_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Progress CSV",
        data=csv,
        file_name="study_progress.csv",
        mime="text/csv"
    )

def reset_progress_data():
    if not st.session_state.authenticated:
        st.warning("Please sign in to reset progress.")
        return
    
    st.session_state.progress_data = {}
    st.session_state.study_hours = 0
    st.session_state.streak_counter = 0
    st.session_state.badges = []
    st.session_state.schedule_data = []
    try:
        progress_ref = db.collection('progress').where(
            filter=firestore.FieldFilter('user_id', '==', st.session_state.user_id)
        )
        docs = progress_ref.stream()
        for doc in docs:
            doc.reference.delete()
        badges_ref = db.collection('badges').where(
            filter=firestore.FieldFilter('user_id', '==', st.session_state.user_id)
        )
        docs = badges_ref.stream()
        for doc in docs:
            doc.reference.delete()
        sessions_ref = db.collection('study_sessions').where(
            filter=firestore.FieldFilter('user_id', '==', st.session_state.user_id)
        )
        docs = sessions_ref.stream()
        for doc in docs:
            doc.reference.delete()
        db.collection('users').document(st.session_state.user_id).update({'curriculum_csv': firestore.DELETE_FIELD})
        st.session_state.curriculum_file = None
        st.session_state.curriculum_data = None
        st.success("✅ Progress data reset!")
    except Exception as e:
        st.error(f"Error resetting progress in Firestore: {str(e)}")

def upload_curriculum_to_firestore(user_id, file):
    try:
        csv_string = file.getvalue().decode("utf-8")
        db.collection('users').document(user_id).set({'curriculum_csv': csv_string}, merge=True)
        return True
    except Exception as e:
        st.error(f"Error uploading curriculum: {str(e)}")
        return False

def download_curriculum_from_firestore(user_id):
    try:
        user_doc = db.collection('users').document(user_id).get()
        if user_doc.exists:
            csv_string = user_doc.to_dict().get('curriculum_csv')
            if csv_string:
                return io.StringIO(csv_string)
        return None
    except Exception as e:
        st.error(f"Error downloading curriculum: {str(e)}")
        return None

def main():
    st.sidebar.title("📚 Navigation")
    
    if st.session_state.authenticated:
        page = st.sidebar.radio(
            "Choose Page",
            ["📊 Dashboard", "📋 Checklist", "🏆 Trophy Case", "📅 Schedule", "⚙️ Settings"],
            label_visibility="collapsed"
        )
    else:
        page = "⚙️ Settings"
    
    if st.session_state.authenticated and st.session_state.curriculum_data:
        completion_percentage, completed_subtopics, total_subtopics, total_modules = calculate_progress_stats(
            st.session_state.progress_data, st.session_state.curriculum_data
        )
        
        st.sidebar.markdown("---")
        st.sidebar.metric("Progress", f"{completion_percentage:.1f}%", help="Your overall completion percentage")
        st.sidebar.metric("Completed", f"{completed_subtopics}/{total_subtopics}", help="Subtopics completed vs total")
        st.sidebar.metric("Study Hours", st.session_state.study_hours, help="Total hours logged")
        st.sidebar.metric("Streak", f"{st.session_state.streak_counter} days", help="Consecutive study days")
    
    if st.session_state.authenticated:
        st.sidebar.markdown("---")
        if st.sidebar.button("➕ Log Study Session", help="Log a new study session"):
            st.session_state.study_hours += 1
            st.session_state.streak_counter += 1
            st.session_state.last_study_date = datetime.now().date()
            save_study_session_to_supabase(st.session_state.user_id, 1)
            st.sidebar.success("Study session logged!")
    
    if page == "📊 Dashboard":
        render_progress_dashboard()
    elif page == "📋 Checklist":
        render_curriculum_checklist()
    elif page == "🏆 Trophy Case":
        render_trophy_case()
    elif page == "📅 Schedule":
        render_study_schedule()
    elif page == "⚙️ Settings":
        render_settings()

if __name__ == "__main__":
    main()
