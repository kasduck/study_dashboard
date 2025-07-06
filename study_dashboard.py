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
from dotenv import load_dotenv
import os
import random
from google.cloud import storage

# Load environment variables
load_dotenv()

# Initialize Firebase app only if not already initialized
try:
    _ = firestore.client()
except ValueError:
    firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if firebase_json:
        cred = credentials.Certificate(json.loads(firebase_json))
        initialize_app(cred, {'projectId': os.getenv("FIREBASE_PROJECT_ID")})
    else:
        raise ValueError("FIREBASE_SERVICE_ACCOUNT_JSON not set")

# Get Firestore client
db = firestore.client()

# Initialize Firebase Storage client
# storage_client = storage.Client()
# bucket = storage_client.bucket(os.getenv("FIREBASE_STORAGE_BUCKET"))  # Set this env var to your bucket name

# Page Configuration
st.set_page_config(
    page_title="Study Progress Dashboard",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Material Design-inspired styling with improved text visibility
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .stats-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 0.5rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .progress-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 0.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .badge-card {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .locked-item {
        opacity: 0.5;
        filter: grayscale(100%);
        color: #000000; /* Black for visibility */
    }
    
    .completed-item {
        background-color: #e8f5e8;
        border-left: 4px solid #28a745;
        color: #000000; /* Black for visibility */
    }
    
    .next-item {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        color: #000000; /* Black for visibility */
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    
    .motivational-quote {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-style: italic;
        margin: 1rem 0;
    }
    
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }
    
    .confetti {
        position: fixed;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 1000;
    }
    
    .message-box {
        padding: 0.5rem;
        margin-top: 0.2rem;
        border-radius: 5px;
        text-align: center;
        background-color: #e8f5e8; /* Greenish background for success */
        color: #000000; /* Black text for visibility */
        border: 2px solid #28a745; /* Green border */
    }
    .message-box.warning {
        background-color: #fff3cd; /* Yellowish background for warning */
        border: 2px solid #ffc107; /* Yellow border */
    }
    .completion-message {
        color: #333333;
        font-size: 1rem;
        margin: 0.5rem 0 1.5rem 0;
        background: none;
        border: none;
        padding: 0;
        box-shadow: none;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.curriculum_data = None
    st.session_state.curriculum_file = None  # <-- Add this line
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
    """Return a random motivational quote"""
    return random.choice(MOTIVATIONAL_QUOTES)

def load_curriculum_data():
    """Load and parse curriculum data from uploaded CSV file or default"""
    if 'curriculum_file' not in st.session_state or st.session_state.curriculum_file is None:
        st.warning("Please upload a curriculum CSV file to populate the checklist.")
        return {}
    
    try:
        # Read the uploaded CSV file
        df = pd.read_csv(st.session_state.curriculum_file)
        
        # Initialize the curriculum dictionary
        curriculum_data = {}
        
        # Group by Module and Chapter
        for (module, chapter), group in df.groupby(['Module', 'Chapter']):
            # Collect all subtopics for this chapter
            subtopics = group['Subtopic'].tolist()
            # Use the first project entry for the chapter (assuming one project per chapter)
            project = group['Project'].iloc[0] if not group['Project'].empty else ""
            
            # Add to curriculum dictionary
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
    """Sign in with Firebase Authentication"""
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
    """Sign up with Firebase Authentication and auto-sign in"""
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
    """Sign out from Firebase Authentication"""
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
    """Sync progress, badges, and study sessions from Firestore"""
    try:
        # Fetch progress
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
        
        # Fetch badges
        badges_ref = db.collection('badges').where(
            filter=firestore.FieldFilter('user_id', '==', user_id)
        )
        docs = badges_ref.stream()
        st.session_state.badges = [doc.to_dict()['badge_name'] for doc in docs]
        
        # Fetch study sessions for study_hours and streak
        sessions_ref = db.collection('study_sessions').where(
            filter=firestore.FieldFilter('user_id', '==', user_id)
        )
        docs = sessions_ref.stream()
        st.session_state.study_hours = sum(doc.to_dict().get('hours', 0) for doc in docs)
        st.session_state.streak_counter = len(list(docs)) if docs else 0
    except Exception as e:
        st.error(f"Error syncing data from Firestore: {str(e)}")

def save_progress_to_supabase(user_id, module, chapter, subtopic, completed):
    """Save progress to Firestore"""
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
    """Save badge to Firestore"""
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
    """Save study session to Firestore"""
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
    """Send email notification using SendGrid with detailed error handling"""
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
    """Send push notification using OneSignal with detailed error handling"""
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
    """Calculate overall progress statistics"""
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
    """Render the main progress dashboard"""
    if not st.session_state.authenticated:
        st.warning("Please sign in to access the dashboard.")
        return
    
    st.markdown('<div class="main-header"><h1>📚 Study Progress Dashboard</h1><p>Track your learning journey with gamification!</p></div>', unsafe_allow_html=True)
    
    # Load curriculum data
    if st.session_state.curriculum_data is None:
        st.session_state.curriculum_data = load_curriculum_data()
    
    # Calculate progress statistics
    completion_percentage, completed_subtopics, total_subtopics, total_modules = calculate_progress_stats(
        st.session_state.progress_data, st.session_state.curriculum_data
    )
    
    # Progress Statistics Cards
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
    
    # Motivational Quote
    st.markdown(f'<div class="motivational-quote">💡 {get_motivational_quote()}</div>', unsafe_allow_html=True)
    
    # Progress Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Module completion pie chart
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
            module_names.append(module.split(":")[0])  # Shortened name
        
        fig_pie = px.pie(
            values=module_completion,
            names=module_names,
            title="Module Completion Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Weekly study hours bar chart (sample data)
        weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        hours = [15, 22, 18, 25]  # Sample data
        
        fig_bar = px.bar(
            x=weeks,
            y=hours,
            title="Weekly Study Hours",
            color=hours,
            color_continuous_scale="Blues"
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # New bar chart: Completed subtopics per module from Firestore
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
            module = entry['module'].split(":")[0]  # Shorten module name
            module_counts[module] = module_counts.get(module, 0) + 1
        
        if module_counts:
            modules = list(module_counts.keys())
            counts = list(module_counts.values())
            fig_subtopics = go.Figure(data=[
                go.Bar(
                    x=modules,
                    y=counts,
                    marker_color='#4facfe',  # Blue color for visibility
                    text=counts,
                    textposition='auto'
                )
            ])
            fig_subtopics.update_layout(
                title="Completed Subtopics by Module",
                xaxis_title="Module",
                yaxis_title="Completed Subtopics",
                template="plotly_white"
            )
            st.plotly_chart(fig_subtopics, use_container_width=True)
        else:
            st.info("No completed subtopics yet. Mark some in the Checklist to see the chart!")
    except Exception as e:
        st.error(f"Error fetching progress from Firestore: {str(e)}")

def render_curriculum_checklist():
    """Render the interactive curriculum checklist with strict sequential unlocking"""
    if not st.session_state.authenticated:
        st.warning("Please sign in to access the checklist.")
        return
    
    st.header("📋 Curriculum Checklist")
    
    # Upload curriculum file if not already uploaded
    if st.session_state.curriculum_data is None or st.session_state.curriculum_file is None:
        # Try to load from Firestore first
        if st.session_state.user_id:
            file_obj = download_curriculum_from_firestore(st.session_state.user_id)
            if file_obj:
                st.session_state.curriculum_file = file_obj
                st.session_state.curriculum_data = load_curriculum_data()
        if st.session_state.curriculum_data is None or st.session_state.curriculum_file is None:
            uploaded_file = st.file_uploader("Upload Curriculum CSV", type=["csv"])
            if uploaded_file is not None:
                # Upload to Firestore
                upload_curriculum_to_firestore(st.session_state.user_id, uploaded_file)
                # Reload from Firestore to ensure consistency
                file_obj = download_curriculum_from_firestore(st.session_state.user_id)
                if file_obj:
                    st.session_state.curriculum_file = file_obj
                    st.session_state.curriculum_data = load_curriculum_data()
                    st.rerun()
            else:
                st.warning("Please upload a curriculum CSV file to populate the checklist.")
                return
    
    # Initialize message storage if not present
    if 'completion_messages' not in st.session_state:
        st.session_state.completion_messages = {}
    
    # Search and filter
    search_term = st.text_input("🔍 Search subtopics...", placeholder="Type to search...")
    
    for module, chapters in st.session_state.curriculum_data.items():
        with st.expander(f"📚 {module}", expanded=True):
            for chapter, content in chapters.items():
                st.subheader(f"📖 {chapter}")
                
                # Display subtopics
                for i, subtopic in enumerate(content.get('subtopics', [])):
                    if search_term.lower() in subtopic.lower() or not search_term:
                        key = f"{module}_{chapter}_{subtopic}"
                        
                        # Sequential unlock: first subtopic or previous subtopic completed
                        is_unlocked = i == 0 or (i > 0 and st.session_state.progress_data.get(
                            f"{module}_{chapter}_{content.get('subtopics', [])[i-1]}", False))
                        
                        # Current completion status
                        is_completed = st.session_state.progress_data.get(key, False)
                        
                        col1, col2, col3 = st.columns([1, 8, 1])
                        
                        with col1:
                            if is_unlocked:
                                # Use unique key to prevent checkbox conflicts
                                new_value = st.checkbox(" ", key=f"checkbox_{key}", value=is_completed)
                                if new_value != is_completed:
                                    if save_progress_to_supabase(st.session_state.user_id, module, chapter, subtopic, new_value):
                                        st.session_state.progress_data[key] = new_value
                                        if new_value:
                                            st.session_state.study_hours += 2
                                            check_and_award_badges()
                                            # Store success message
                                            st.session_state.completion_messages[key] = f"🎉 Subtopic '{subtopic}' completed!"
                                        else:
                                            st.session_state.study_hours = max(0, st.session_state.study_hours - 2)
                                            # Store warning message
                                            st.session_state.completion_messages[key] = f"Subtopic '{subtopic}' marked incomplete."
                                        # Force rerender to update UI
                                        st.rerun()
                            else:
                                st.markdown("🔒")
                        
                        with col2:
                            if is_completed:
                                st.markdown(f'<div class="completed-item">✅ {subtopic}</div>', unsafe_allow_html=True)
                            elif is_unlocked:
                                st.markdown(f'<div class="next-item">⏳ {subtopic}</div>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<div class="locked-item">🔒 {subtopic}</div>', unsafe_allow_html=True)
                            # Display persistent message with matching width
                            if key in st.session_state.completion_messages:
                                st.markdown(
                                    f'<div class="message-box" style="width: {len(subtopic) * 0.6}em;">'
                                    f'{st.session_state.completion_messages[key]}</div>',
                                    unsafe_allow_html=True
                                )
                        
                        with col3:
                            if is_completed:
                                st.markdown("✅")
                            elif is_unlocked:
                                st.markdown("⏳")
                            else:
                                st.markdown("🔒")
                
                # Project details
                if 'project' in content:
                    if st.button(f"📋 View Project Details", key=f"project_{module}_{chapter}"):
                        st.info(f"**Project:** {content['project']}")

    # Clear completion messages after rendering
    st.session_state.completion_messages = {}

    # Show completion messages (improved look)
    if st.session_state.completion_messages:
        for msg in st.session_state.completion_messages.values():
            st.markdown(
                f'<div class="completion-message">{msg}</div>',
                unsafe_allow_html=True
            )
        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)  # Extra gap

def check_and_award_badges():
    """Check progress and award badges"""
    if not st.session_state.authenticated:
        return
    
    completion_percentage, completed_subtopics, total_subtopics, total_modules = calculate_progress_stats(
        st.session_state.progress_data, st.session_state.curriculum_data
    )
    
    # Badge criteria
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
    
    # Award new badges
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
    """Render the trophy case with earned badges"""
    if not st.session_state.authenticated:
        st.warning("Please sign in to view your trophy case.")
        return
    
    st.header("🏆 Trophy Case")
    
    if not st.session_state.badges:
        st.info("Complete subtopics to earn badges!")
        return
    
    # Display badges in a grid
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

@st.dialog("Confirm Reset")
def reset_dialog():
    st.write("Are you sure you want to reset all progress?")
    if st.button("Yes, Reset All Progress"):
        reset_progress_data()
        st.rerun()

def render_study_schedule():
    """Render study schedule and calendar"""
    if not st.session_state.authenticated:
        st.warning("Please sign in to access the schedule.")
        return
    
    st.header("📅 Study Schedule")
    
    # Time allocation settings
    st.subheader("⚙️ Schedule Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        daily_hours = st.slider("Daily Study Hours", 2, 8, 4)
        start_time = st.time_input("Preferred Start Time", value=datetime.strptime("09:00", "%H:%M").time())
    
    with col2:
        study_days = st.multiselect(
            "Available Days",
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            default=["Monday", "Saturday", "Sunday"]
        )
    
    # Generate schedule
    if st.button("🗓️ Generate Schedule"):
        generate_study_schedule(daily_hours, start_time, study_days)
    
    # Display current schedule
    if st.session_state.schedule_data:
        st.subheader("📋 Current Schedule")
        schedule_df = pd.DataFrame(st.session_state.schedule_data)
        st.dataframe(schedule_df, use_container_width=True)
        
        # Weekly Goal Tracking
        weekly_hours = st.session_state.study_hours % 7  # Current week's hours
        target_hours = 25  # Midpoint of 20-30 hours/week
        fig_goal = go.Figure(data=[go.Indicator(
            value=weekly_hours,
            mode="gauge+number",
            title={'text': "Weekly Hours Progress"},
            gauge={'axis': {'range': [0, 30]}}
        )])
        st.plotly_chart(fig_goal, use_container_width=True)
        
        # Export to calendar
        if st.button("📄 Export to Calendar (.ics)"):
            export_to_calendar()

def generate_study_schedule(daily_hours, start_time, study_days):
    """Generate a study schedule based on preferences"""
    # Clear existing schedule
    st.session_state.schedule_data = []
    
    # Get uncompleted subtopics with deadlines
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
                        'estimated_hours': 2,  # Default 2 hours per subtopic
                        'deadline': content.get('deadline', '9999-12-31')  # Default far future if no deadline
                    })
    
    # Sort by deadline for priority
    uncompleted_subtopics.sort(key=lambda x: x['deadline'])
    
    # Schedule subtopics
    current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = current_date + timedelta(days=14)  # Limit to 2 weeks
    scheduled_hours = 0
    target_weekly_hours = 25  # Midpoint of 20-30 hours/week
    
    while current_date <= end_date and uncompleted_subtopics and scheduled_hours < target_weekly_hours:
        day_name = current_date.strftime("%A")
        if day_name in study_days:
            # Avoid Tuesday-Friday 12 PM to 8 PM
            is_restricted = day_name in ["Tuesday", "Wednesday", "Thursday", "Friday"] and start_time.hour >= 12 and start_time.hour < 20
            if not is_restricted:
                session_duration = min(daily_hours, 3)  # Cap at 3 hours for intelligent blocking
                if uncompleted_subtopics:
                    subtopic_data = uncompleted_subtopics.pop(0)  # Take earliest deadline
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
    """Export schedule to .ics calendar file"""
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
    
    # Create download link
    ics_content = cal.to_ical().decode('utf-8')
    st.download_button(
        label="📥 Download Calendar File",
        data=ics_content,
        file_name="study_schedule.ics",
        mime="text/calendar"
    )

def export_supabase_data():
    """Export progress and badges from Firestore as CSV"""
    if not st.session_state.authenticated:
        st.warning("Please sign in to export data.")
        return
    
    try:
        # Fetch progress data
        progress_ref = db.collection('progress').where(
            filter=firestore.FieldFilter('user_id', '==', st.session_state.user_id)
        )
        docs = progress_ref.stream()
        progress_data = [doc.to_dict() for doc in docs]
        progress_df = pd.DataFrame(progress_data)
        progress_csv = progress_df.to_csv(index=False)
        
        # Fetch badges data
        badges_ref = db.collection('badges').where(
            filter=firestore.FieldFilter('user_id', '==', st.session_state.user_id)
        )
        docs = badges_ref.stream()
        badges_data = [doc.to_dict() for doc in docs]
        badges_df = pd.DataFrame(badges_data)
        badges_csv = badges_df.to_csv(index=False)
        
        # Create download buttons
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
    """Render settings and preferences"""
    st.header("⚙️ Settings")
    
    # Authentication
    if not st.session_state.authenticated:
        st.subheader("👤 Authentication")
        email = st.text_input("📧 Email")
        password = st.text_input("🔒 Password", type="password")
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
    
    # User preferences (only show if authenticated)
    if st.session_state.authenticated:
        st.subheader("👤 User Preferences")
        col1, col2 = st.columns(2)
        
        with col1:
            st.session_state.user_email = st.text_input("📧 Email", value=st.session_state.user_email, disabled=True)
            st.session_state.dark_mode = st.checkbox("🌙 Dark Mode", value=st.session_state.dark_mode)
        
        with col2:
            st.session_state.notifications_enabled = st.checkbox("🔔 Enable Notifications", value=st.session_state.notifications_enabled)
            notification_frequency = st.selectbox("📅 Notification Frequency", ["Daily", "Weekly", "Monthly"])
        
        # Data management
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

def export_progress_data():
    """Export progress data as CSV"""
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
    """Reset all progress data"""
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
        # Remove curriculum CSV from Firestore
        db.collection('users').document(st.session_state.user_id).update({'curriculum_csv': firestore.DELETE_FIELD})
        st.session_state.curriculum_file = None
        st.session_state.curriculum_data = None
        st.success("✅ Progress data reset!")
    except Exception as e:
        st.error(f"Error resetting progress in Firestore: {str(e)}")

def upload_curriculum_to_storage(user_id, file):
    """Upload curriculum CSV to Firebase Storage and return the blob path"""
    try:
        blob_path = f"curriculums/{user_id}/curriculum.csv"
        blob = bucket.blob(blob_path)
        blob.upload_from_file(file, content_type="text/csv")
        # Optionally, save the blob path in Firestore for reference
        db.collection('users').document(user_id).set({'curriculum_blob': blob_path}, merge=True)
        return blob_path
    except Exception as e:
        st.error(f"Error uploading curriculum: {str(e)}")
        return None

def download_curriculum_from_storage(user_id):
    """Download curriculum CSV from Firebase Storage and return as BytesIO"""
    try:
        user_doc = db.collection('users').document(user_id).get()
        blob_path = None
        if user_doc.exists:
            blob_path = user_doc.to_dict().get('curriculum_blob')
        if not blob_path:
            return None
        blob = bucket.blob(blob_path)
        if blob.exists():
            file_bytes = blob.download_as_bytes()
            return io.BytesIO(file_bytes)
        else:
            return None
    except Exception as e:
        st.error(f"Error downloading curriculum: {str(e)}")
        return None

def upload_curriculum_to_firestore(user_id, file):
    """Upload curriculum CSV content to Firestore as a string"""
    try:
        csv_string = file.getvalue().decode("utf-8")
        db.collection('users').document(user_id).set({'curriculum_csv': csv_string}, merge=True)
        return True
    except Exception as e:
        st.error(f"Error uploading curriculum: {str(e)}")
        return False

def download_curriculum_from_firestore(user_id):
    """Download curriculum CSV content from Firestore and return as StringIO"""
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
    """Main application function"""
    # Sidebar navigation
    st.sidebar.title("📚 Navigation")
    
    if st.session_state.authenticated:
        page = st.sidebar.radio(
            "Choose Page",
            ["📊 Dashboard", "📋 Checklist", "🏆 Trophy Case", "📅 Schedule", "⚙️ Settings"]
        )
    else:
        page = "⚙️ Settings"
    
    # Quick stats in sidebar
    if st.session_state.authenticated and st.session_state.curriculum_data:
        completion_percentage, completed_subtopics, total_subtopics, total_modules = calculate_progress_stats(
            st.session_state.progress_data, st.session_state.curriculum_data
        )
        
        st.sidebar.markdown("---")
        st.sidebar.metric("Progress", f"{completion_percentage:.1f}%")
        st.sidebar.metric("Completed", f"{completed_subtopics}/{total_subtopics}")
        st.sidebar.metric("Study Hours", st.session_state.study_hours)
        st.sidebar.metric("Streak", f"{st.session_state.streak_counter} days")
    
    # Add study hours button
    if st.session_state.authenticated:
        st.sidebar.markdown("---")
        if st.sidebar.button("➕ Log Study Session"):
            st.session_state.study_hours += 1
            st.session_state.streak_counter += 1
            st.session_state.last_study_date = datetime.now().date()
            save_study_session_to_supabase(st.session_state.user_id, 1)
            st.sidebar.success("Study session logged!")
    
    # Main content area
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
