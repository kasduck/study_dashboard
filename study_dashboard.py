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
import re
import random

# Initialize Firebase app only if not already initialized
try:
    _ = firestore.client()
except ValueError:
    try:
        firebase_json = st.secrets["firebase"]["FIREBASE_SERVICE_ACCOUNT_JSON"]
        firebase_json = firebase_json.strip()
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

# Get Firestore client
db = firestore.client()

# Page Configuration
st.set_page_config(
    page_title="Study Progress Dashboard",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for improved UI/UX
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #4facfe 0%, #3b8aff 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .main-header h1 {
        font-size: 2.2rem;
        font-weight: 600;
    }
    .main-header p {
        font-size: 1.1rem;
        opacity: 0.9;
    }
    .stats-card {
        background: #4facfe;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    }
    .stats-card h3 {
        font-size: 1.2rem;
    }
    .stats-card h2 {
        font-size: 1.8rem;
    }
    .progress-card {
        background: #43e97b;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    }
    .badge-card {
        background: #f093fb;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        position: relative;
    }
    .locked-item {
        opacity: 0.5;
        filter: grayscale(100%);
        color: #000000;
        position: relative;
    }
    .completed-item {
        background-color: #e8f5e8;
        border-left: 4px solid #28a745;
        color: #000000;
    }
    .next-item {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        color: #000000;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    .motivational-quote {
        background: #4facfe;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        font-style: italic;
        margin: 1rem 0;
    }
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }
    .tooltip .tooltip-text {
        visibility: hidden;
        width: 200px;
        background-color: #333;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 5px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -100px;
        opacity: 0;
        transition: opacity 0.3s;
    }
    .tooltip:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }
    .badge-card .tooltip-text {
        width: 150px;
        margin-left: -75px;
    }
    .message-box {
        padding: 0.5rem;
        margin-top: 0.2rem;
        border-radius: 5px;
        text-align: center;
        background-color: #e8f5e8;
        color: #000000;
        border: 2px solid #28a745;
        animation: fadeOut 5s forwards;
    }
    .message-box.warning {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
    }
    @keyframes fadeOut {
        0% { opacity: 1; }
        80% { opacity: 1; }
        100% { opacity: 0; display: none; }
    }
    .stButton>button {
        aria-label: "Button action";
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #3b8aff;
    }
    .stCheckbox>label>input {
        outline: none;
    }
    .stCheckbox>label>input:focus {
        outline: 2px solid #4facfe;
    }
    .stRadio > div > label > div {
        padding: 0.5rem;
        border-radius: 5px;
    }
    .stRadio > div > label > input:checked + div {
        background-color: #e8f5e8;
        font-weight: 600;
    }
    .stSidebar {
        max-height: 80vh;
        overflow-y: auto;
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
    st.session_state.high_contrast = False
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
    """Return a deterministic motivational quote based on the current day"""
    day_index = datetime.now().timetuple().tm_yday % len(MOTIVATIONAL_QUOTES)
    return MOTIVATIONAL_QUOTES[day_index]

def load_curriculum_data():
    """Load and parse curriculum data from uploaded CSV file or default"""
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
        st.session_state.study_hours = sum(doc.to_dict().get('hours', 0) for doc in docs)
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
    st.markdown('<div class="main-header"><h1>📚 Study Progress Dashboard</h1><p>Track your learning journey with gamification!</p></div>', unsafe_allow_html=True)
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
    if st.button("🔄 New Quote", key="refresh_quote"):
        MOTIVATIONAL_QUOTES.append(MOTIVATIONAL_QUOTES.pop(0))
        st.rerun()
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
            color_discrete_sequence=['#4facfe', '#00f2fe', '#43e97b', '#f093fb', '#f5576c']
        )
        fig_pie.update_traces(hovertemplate="%{label}: %{value:.1f}%")
        fig_pie.update_layout(
            template="plotly_white",
            font=dict(size=14),
            margin=dict(l=20, r=20, t=50, b=20),
            transition_duration=500
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
            color_continuous_scale="Blues"
        )
        fig_bar.update_layout(
            template="plotly_white",
            font=dict(size=14),
            margin=dict(l=20, r=20, t=50, b=20),
            transition_duration=500
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
                    marker_color='#4facfe',
                    text=counts,
                    textposition='auto'
                )
            ])
            fig_subtopics.update_layout(
                title="Completed Subtopics by Module",
                xaxis_title="Module",
                yaxis_title="Completed Subtopics",
                template="plotly_white",
                font=dict(size=14),
                margin=dict(l=20, r=20, t=50, b=20),
                transition_duration=500
            )
            st.plotly_chart(fig_subtopics, use_container_width=True)
        else:
            st.info("No completed subtopics yet. Mark some in the Checklist to see the chart!")
    except Exception as e:
        st.error(f"Error fetching progress from Firestore: {str(e)}")

def render_curriculum_checklist():
    st.header("📋 Curriculum Checklist")
    if not st.session_state.authenticated:
        st.warning("Please sign in to access the checklist.")
        return
    if st.session_state.curriculum_data is None or st.session_state.curriculum_file is None:
        file_obj = download_curriculum_from_firestore(st.session_state.user_id)
        if file_obj:
            st.session_state.curriculum_file = file_obj
            st.session_state.curriculum_data = load_curriculum_data()
        if st.session_state.curriculum_data is None or st.session_state.curriculum_file is None:
            uploaded_file = st.file_uploader("Upload Curriculum CSV", type=["csv"], key="curriculum_upload")
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
    with st.expander("🔍 Search Subtopics", expanded=False):
        search_term = st.text_input("", placeholder="Type to search...", key="search_subtopics")
    for module, chapters in st.session_state.curriculum_data.items():
        total_subtopics = sum(len(content.get('subtopics', [])) for chapter, content in chapters.items())
        completed_subtopics = sum(1 for chapter, content in chapters.items() for subtopic in content.get('subtopics', []) if st.session_state.progress_data.get(f"{module}_{chapter}_{subtopic}", False))
        module_progress = (completed_subtopics / total_subtopics * 100) if total_subtopics > 0 else 0
        with st.expander(f"📚 {module} ({module_progress:.1f}% Complete)", expanded=True):
            for chapter, content in chapters.items():
                chapter_subtopics = len(content.get('subtopics', []))
                chapter_completed = sum(1 for subtopic in content.get('subtopics', []) if st.session_state.progress_data.get(f"{module}_{chapter}_{subtopic}", False))
                chapter_progress = (chapter_completed / chapter_subtopics * 100) if chapter_subtopics > 0 else 0
                st.subheader(f"📖 {chapter} ({chapter_progress:.1f}% Complete)")
                for i, subtopic in enumerate(content.get('subtopics', [])):
                    if search_term.lower() in subtopic.lower() or not search_term:
                        key = f"{module}_{chapter}_{subtopic}"
                        is_unlocked = i == 0 or (i > 0 and st.session_state.progress_data.get(f"{module}_{chapter}_{content.get('subtopics', [])[i-1]}", False))
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
                                st.markdown("🔒")
                        with col2:
                            if is_completed:
                                st.markdown(f'<div class="completed-item">✅ {subtopic}</div>', unsafe_allow_html=True)
                            elif is_unlocked:
                                st.markdown(f'<div class="next-item">⏳ {subtopic}</div>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<div class="locked-item tooltip">🔒 {subtopic}<span class="tooltip-text">Complete the previous subtopic to unlock</span></div>', unsafe_allow_html=True)
                            if key in st.session_state.completion_messages:
                                st.markdown(
                                    f'<div class="message-box" style="width: {len(subtopic) * 0.6}em;">'
                                    f'{st.session_state.completion_messages[key]}'
                                    f'<button onclick="this.parentElement.style.display=\'none\'" style="float:right; border:none; background:none; cursor:pointer;">✖</button></div>',
                                    unsafe_allow_html=True
                                )
                        with col3:
                            if is_completed:
                                st.markdown("✅")
                            elif is_unlocked:
                                st.markdown("⏳")
                            else:
                                st.markdown("🔒")
                if 'project' in content:
                    if st.button(f"📋 View Project Details", key=f"project_{module}_{chapter}", help="View project details for this chapter"):
                        st.info(f"**Project:** {content['project']}")
    st.session_state.completion_messages = {}

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
    st.header("🏆 Trophy Case")
    if not st.session_state.badges:
        st.info("Complete subtopics to earn badges!")
        return
    badge_descriptions = {
        "First Steps": "Completed 5 subtopics",
        "Getting Started": "Completed 10 subtopics",
        "Quarter Master": "Reached 25% completion",
        "Halfway Hero": "Reached 50% completion",
        "Streak Star": "Maintained a 5-day streak",
        "Study Master": "Logged 50 study hours",
        "Module Master": "Completed an entire module"
    }
    badge_icons = {
        "First Steps": "🚀",
        "Getting Started": "⭐",
        "Quarter Master": "🎯",
        "Halfway Hero": "🦸",
        "Streak Star": "🔥",
        "Study Master": "📚",
        "Module Master": "🎓"
    }
    sort_by = st.selectbox("Sort Badges By", ["Name", "Date Earned"], key="sort_badges")
    sorted_badges = st.session_state.badges
    if sort_by == "Date Earned":
        badges_ref = db.collection('badges').where(
            filter=firestore.FieldFilter('user_id', '==', st.session_state.user_id)
        )
        docs = badges_ref.stream()
        badge_data = [(doc.to_dict()['badge_name'], doc.to_dict().get('earned_at', firestore.SERVER_TIMESTAMP)) for doc in docs]
        sorted_badges = [badge for badge, _ in sorted(badge_data, key=lambda x: x[1], reverse=True)]
    else:
        sorted_badges = sorted(st.session_state.badges)
    cols = st.columns(4)
    for i, badge in enumerate(sorted_badges):
        col = cols[i % 4]
        with col:
            icon = badge_icons.get(badge, "🏆")
            st.markdown(
                f"""
                <div class="badge-card tooltip">
                    <h2>{icon}</h2>
                    <h4>{badge}</h4>
                    <span class="tooltip-text">{badge_descriptions.get(badge, "Earned for outstanding progress!")}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

@st.dialog("Confirm Reset")
def reset_dialog():
    st.write("Are you sure you want to reset all progress?")
    if st.button("Yes, Reset All Progress", key="confirm_reset"):
        reset_progress_data()
        st.rerun()

def render_study_schedule():
    if not st.session_state.authenticated:
        st.warning("Please sign in to access the schedule.")
        return
    st.header("📅 Study Schedule")
    st.subheader("⚙️ Schedule Settings")
    col1, col2 = st.columns(2)
    with col1:
        daily_hours = st.slider("Daily Study Hours", 2, 8, 4, key="daily_hours")
        start_time = st.time_input("Preferred Start Time", value=datetime.strptime("09:00", "%H:%M").time(), key="start_time")
    with col2:
        study_days = st.multiselect(
            "Available Days",
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            default=["Monday", "Saturday", "Sunday"],
            key="study_days"
        )
    if st.button("🗓️ Generate Schedule", key="generate_schedule", help="Generate a new study schedule"):
        generate_study_schedule(daily_hours, start_time, study_days)
    if st.session_state.schedule_data:
        st.subheader("📋 Current Schedule")
        sort_by = st.selectbox("Sort Schedule By", ["Date", "Urgent", "Module"], key="sort_schedule")
        schedule_df = pd.DataFrame(st.session_state.schedule_data)
        if sort_by == "Urgent":
            schedule_df = schedule_df.sort_values(by="Urgent", ascending=False)
        elif sort_by == "Module":
            schedule_df = schedule_df.sort_values(by="Module")
        else:
            schedule_df = schedule_df.sort_values(by="Date")
        def highlight_urgent(row):
            return ['background-color: #fff3cd' if row['Urgent'] else '' for _ in row]
        st.dataframe(schedule_df.style.apply(highlight_urgent, axis=1), use_container_width=True)
        weekly_hours = st.session_state.study_hours % 7
        target_hours = 25
        fig_goal = go.Figure(data=[go.Indicator(
            value=weekly_hours,
            mode="gauge+number",
            title={'text': "Weekly Hours Progress"},
            gauge={'axis': {'range': [0, 30]}}
        )])
        fig_goal.update_layout(
            template="plotly_white",
            font=dict(size=14),
            margin=dict(l=20, r=20, t=50, b=20),
            transition_duration=500
        )
        st.plotly_chart(fig_goal, use_container_width=True)
        if st.button("📄 Export to Calendar (.ics)", key="export_calendar", help="Export schedule to calendar file"):
            export_to_calendar()

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
            mime="text/csv",
            key="download_progress"
        )
        st.download_button(
            label="Download Badges CSV",
            data=badges_csv,
            file_name="firestore_badges.csv",
            mime="text/csv",
            key="download_badges"
        )
    except Exception as e:
        st.error(f"Error exporting Firestore data: {str(e)}")

def render_settings():
    st.header("⚙️ Settings")
    with st.expander("👤 Authentication", expanded=not st.session_state.authenticated):
        if not st.session_state.authenticated:
            email = st.text_input("📧 Email", key="auth_email", help="Enter your email address")
            password = st.text_input("🔒 Password", type="password", key="auth_password", help="Enter your password")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Sign In", key="sign_in", help="Sign in to your account"):
                    sign_in(email, password)
            with col2:
                if st.button("Sign Up", key="sign_up", help="Create a new account"):
                    sign_up(email, password)
        else:
            st.write(f"Logged in as: {st.session_state.user_email}")
            if st.button("Sign Out", key="sign_out", help="Sign out of your account"):
                sign_out()
    if st.session_state.authenticated:
        with st.expander("👤 User Preferences", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.user_email = st.text_input("📧 Email", value=st.session_state.user_email, disabled=True, key="settings_email")
                st.session_state.dark_mode = st.checkbox("🌙 Dark Mode", value=st.session_state.dark_mode, key="dark_mode", help="Enable dark mode for better visibility in low light")
                st.session_state.high_contrast = st.checkbox("👓 High Contrast Mode", value=st.session_state.get('high_contrast', False), key="high_contrast", help="Enable high contrast for better accessibility")
            with col2:
                st.session_state.notifications_enabled = st.checkbox("🔔 Enable Notifications", value=st.session_state.notifications_enabled, key="notifications", help="Receive email and push notifications for progress and badges")
                notification_frequency = st.selectbox("📅 Notification Frequency", ["Daily", "Weekly", "Monthly"], key="notification_freq", help="Choose how often to receive notifications")
        if st.session_state.get('high_contrast', False):
            st.markdown("""
            <style>
                .main-header, .stats-card, .progress-card, .badge-card, .motivational-quote {
                    background: #000000 !important;
                    color: #FFFFFF !important;
                    border: 2px solid #FFFFFF;
                }
                .completed-item, .next-item, .locked-item {
                    color: #000000 !important;
                    background: #FFFFFF !important;
                }
            </style>
            """, unsafe_allow_html=True)
        with st.expander("💾 Data Management"):
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📤 Export Progress", key="export_progress", help="Export progress data as CSV"):
                    export_progress_data()
            with col2:
                if st.button("🔄 Reset Progress", key="reset_progress", help="Reset all progress data"):
                    reset_dialog()
            with col3:
                if st.button("📥 Export Firestore Data", key="export_firestore", help="Export Firestore data as CSV"):
                    export_supabase_data()

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
        mime="text/csv",
        key="download_study_progress"
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
            key="nav_radio"
        )
    else:
        page = "⚙️ Settings"
    if st.session_state.authenticated and st.session_state.curriculum_data:
        completion_percentage, completed_subtopics, total_subtopics, total_modules = calculate_progress_stats(
            st.session_state.progress_data, st.session_state.curriculum_data
        )
        st.sidebar.markdown("### Progress Overview")
        st.sidebar.metric("Progress", f"{completion_percentage:.1f}%")
        st.sidebar.metric("Completed", f"{completed_subtopics}/{total_subtopics}")
        st.sidebar.metric("Study Hours", st.session_state.study_hours)
        st.sidebar.metric("Streak", f"{st.session_state.streak_counter} days")
    st.sidebar.markdown("### Actions")
    if st.session_state.authenticated:
        if st.sidebar.button("➕ Log Study Session", key="log_session", help="Log a new study session"):
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
