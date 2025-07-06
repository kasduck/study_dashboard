# 📚 Gamified Study Dashboard - Complete Setup Guide

## 🚀 Quick Start

This dashboard helps you track your study progress with gamification elements including badges, streaks, and interactive visualizations.

## 📋 Prerequisites

- Python 3.8+
- Git
- Streamlit Community Cloud account (optional for deployment)
- Supabase account (optional for cloud database)
- SendGrid account (optional for email notifications)
- OneSignal account (optional for push notifications)

## 🔧 Installation

### 1. Clone or Download the Files

Create a new directory and save the following files:
- `study_dashboard.py` (main application)
- `requirements.txt` (dependencies)
- `curriculum.csv` (your course data - optional)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Locally

```bash
streamlit run study_dashboard.py
```

The application will open in your browser at `http://localhost:8501`

## 🎯 Core Features

### Dashboard Overview
- **Progress Tracking**: Visual progress bars and completion percentages
- **Gamification**: Badges, streaks, and achievement system
- **Statistics**: Study hours, completion rates, and progress analytics
- **Interactive Charts**: Module completion pie charts and weekly study hours

### Curriculum Checklist
- **Sequential Learning**: Subtopics unlock as you complete previous ones
- **Search Functionality**: Find specific topics quickly
- **Progress Marking**: Check off completed subtopics
- **Project Details**: View project requirements for each chapter

### Trophy Case
- **Badge System**: Earn badges for various achievements
- **Achievement Tracking**: Visual display of earned badges
- **Motivation**: Gamified progress tracking

### Study Schedule
- **Schedule Generator**: Create personalized study schedules
- **Calendar Export**: Export to .ics calendar files
- **Time Management**: Set daily hours and preferred times

## 🔑 Optional Service Setup

### Supabase Setup (For Cloud Database)

1. **Create Account**: Go to [supabase.com](https://supabase.com) and create a free account
2. **Create Project**: Create a new project and note your project URL and anon key
3. **Database Schema**: Create the following tables:

```sql
-- Users table
CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Progress table
CREATE TABLE progress (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    module TEXT NOT NULL,
    chapter TEXT NOT NULL,
    subtopic TEXT NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Study sessions table
CREATE TABLE study_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    date DATE NOT NULL,
    hours INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Badges table
CREATE TABLE badges (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    badge_name TEXT NOT NULL,
    earned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

4. **Authentication**: Enable email authentication in Supabase Auth settings
5. **Environment Variables**: Create a `.env` file with:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

### SendGrid Setup (For Email Notifications)

1. **Create Account**: Go to [sendgrid.com](https://sendgrid.com) and create a free account
2. **API Key**: Create an API key in Settings > API Keys
3. **Verify Sender**: Add and verify your sender email address
4. **Environment Variables**: Add to your `.env` file:
```
SENDGRID_API_KEY=your_sendgrid_api_key
FROM_EMAIL=your_verified_sender_email
```

### OneSignal Setup (For Push Notifications)

1. **Create Account**: Go to [onesignal.com](https://onesignal.com) and create a free account
2. **Create App**: Create a new web app
3. **Get App ID**: Note your App ID and API Key
4. **Environment Variables**: Add to your `.env` file:
```
ONESIGNAL_APP_ID=your_onesignal_app_id
ONESIGNAL_API_KEY=your_onesignal_api_key
```

## 🎨 Customization

### Adding Your Own Curriculum

1. **Edit the Code**: Modify the `load_curriculum_data()` function in `study_dashboard.py`
2. **Structure**: Follow this format:
```python
data = {
    "Module Name": {
        "Chapter Name": {
            "subtopics": [
                "Subtopic 1",
                "Subtopic 2",
                # ... more subtopics
            ],
            "project": "Project description here"
        }
    }
}
```

### Customizing Badge System

Edit the `check_and_award_badges()` function to add new badges:
```python
if your_condition and "Badge Name" not in st.session_state.badges:
    badges_to_award.append("Badge Name")
```

### Styling Customization

Modify the CSS in the `st.markdown()` section at the top of the file to change colors, fonts, and layout.

## 🚀 Deployment Options

### Option 1: Streamlit Community Cloud (Recommended)

1. **Push to GitHub**: Upload your code to a GitHub repository
2. **Connect Streamlit**: Go to [share.streamlit.io](https://share.streamlit.io)
3. **Deploy**: Connect your GitHub repo and deploy
4. **Environment Variables**: Add your environment variables in the Streamlit dashboard

### Option 2: Heroku

1. **Create Procfile**:
```
web: streamlit run study_dashboard.py --server.port=$PORT --server.address=0.0.0.0
```

2. **Deploy**: Push to Heroku with the Procfile and requirements.txt

### Option 3: Docker

1. **Create Dockerfile**:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "study_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

2. **Build and Run**:
```bash
docker build -t study-dashboard .
docker run -p 8501:8501 study-dashboard
```

## 🔧 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed with `pip install -r requirements.txt`
2. **Port Issues**: If port 8501 is busy, use `streamlit run study_dashboard.py --server.port=8502`
3. **Memory Issues**: For large datasets, consider using Supabase for data storage

### Performance Tips

- **Local Storage**: The app uses session state for local storage
- **Data Persistence**: Use Supabase for persistent data across sessions
- **Large Datasets**: Consider pagination for large curriculum data

## 📊 Usage Guide

### Getting Started

1. **Launch the App**: Run `streamlit run study_dashboard.py`
2. **Dashboard**: View your overall progress and statistics
3. **Checklist**: Start completing subtopics in order
4. **Schedule**: Generate and export study schedules
5. **Trophy Case**: Check your earned badges

### Best Practices

- **Daily Use**: Log study sessions daily to maintain streaks
- **Sequential Learning**: Complete subtopics in order for optimal learning
- **Regular Scheduling**: Use the schedule generator for consistent study habits
- **Progress Tracking**: Export progress data regularly for backup

### Badge System

- **First Steps**: Complete 5 subtopics
- **Getting Started**: Complete 10 subtopics
- **Quarter Master**: Reach 25% completion
- **Halfway Hero**: Reach 50% completion
- **Streak Star**: Maintain 5+ day study streak
- **Study Master**: Log 50+ study hours

## 🆘 Support

### Documentation
- **Streamlit Docs**: [docs.streamlit.io](https://docs.streamlit.io)
- **Plotly Docs**: [plotly.com/python](https://plotly.com/python/)
- **Pandas Docs**: [pandas.pydata.org](https://pandas.pydata.org/)

### Community
- **Streamlit Community**: [discuss.streamlit.io](https://discuss.streamlit.io)
- **GitHub Issues**: Create issues in your repository for bug reports

### Customization Help
- Modify the `study_dashboard.py` file to add new features
- Check the code comments for guidance on customization
- Use Streamlit's extensive documentation for UI components

## 📈 Future Enhancements

### Potential Features
- **Analytics Dashboard**: Detailed progress analytics
- **Social Features**: Share progress with friends
- **Mobile App**: React Native or Flutter version
- **AI Recommendations**: Personalized study recommendations
- **Integration**: LMS integration capabilities

### Contributing
- Fork the repository
- Create feature branches
- Submit pull requests
- Follow coding standards

---

**Happy Learning! 🎓**

*This dashboard is designed to make studying more engaging and trackable. Customize it to fit your specific learning goals and enjoy the gamified experience!*