from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
from datetime import datetime
import os
from functools import wraps
from .jwt_token import get_clerk_sign_token_for_user

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
CLERK_SECRET_KEY = os.environ.get("CLERK_SECRET_KEY")
ORGANIZATION_ID = os.environ.get("ORGANIZATION_ID")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CLERK_API_BASE = "https://api.clerk.com/v1"

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session or not session['authenticated']:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def check_organization_membership(user_id):
    """Check if the user belongs to the specified organization."""
    url = f"{CLERK_API_BASE}/users/{user_id}/organization_memberships"
    headers = {
        "Authorization": f"Bearer {CLERK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Check if the user belongs to any organization
        if data['total_count'] == 0:
            return False
            
        # Check if the user belongs to the specific organization
        for membership in data['data']:
            if ORGANIZATION_ID == membership['organization'].get('id'):
                return True
                
        return False
    except Exception as e:
        print(f"Error checking organization membership: {e}")
        return False

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        
        if not user_id:
            flash('Please provide a User ID', 'error')
            return render_template('login.html')
        
        if check_organization_membership(user_id):
            session['authenticated'] = True
            session['user_id'] = user_id
            # Generate Clerk Sign Token and store in session
            session['clerk_token'] = get_clerk_sign_token_for_user(user_id)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('You are not authorized to access this application. Please contact your administrator.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/sessions/<time_filter>')
@login_required
def get_filtered_sessions(time_filter):
    try:
        # Get additional filter parameters from the request
        session_id = request.args.get('session_id', None)
        user_id = request.args.get('user_id', None)
        agent_uuid = request.args.get('agent_uuid', None)

        # Prepare parameters for the API request
        params = {"time_filter": time_filter}
        if session_id and session_id != "all":
            params['session_id'] = session_id
        if user_id and user_id != "all":
            params['user_id'] = user_id
        if agent_uuid and agent_uuid != "all":
            params['agent_uuid'] = agent_uuid

        session['clerk_token']= get_clerk_sign_token_for_user(session['user_id'])
        auth_token = session['clerk_token']
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = requests.get(f"{API_BASE_URL}/v2/sessions", params=params, headers=headers)
        data = response.json()
        
        # Calculate summary statistics
        completed_count = sum(1 for session in data['sessions'] if session['status'] == 'completed')
        in_progress_count = sum(1 for session in data['sessions'] if session['status'] == 'in_progress')
        failed_count = sum(1 for session in data['sessions'] if session['status'] == 'failed')

        summary_stats = {
            "completed": completed_count,
            "in_progress": in_progress_count,
            "failed": failed_count,
            "total_sessions": len(data['sessions'])
        }

        return {"sessions": data['sessions'], "summary": summary_stats}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/filter-options/<time_filter>')
@login_required
def get_filter_options(time_filter):
    try:
        session['clerk_token']= get_clerk_sign_token_for_user(session['user_id'])
        auth_token = session['clerk_token']
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = requests.get(f"{API_BASE_URL}/v2/sessions", params={"time_filter": time_filter}, headers=headers)
        data = response.json()

        # Extract unique session_ids, user_ids, and agent_uuids
        session_ids = set(session['session_id'] for session in data['sessions'])
        user_ids = set(session['user_id'] for session in data['sessions'])
        agent_uuids = set(session['agent_uuid'] for session in data['sessions'])

        return {
            "session_ids": list(session_ids),
            "user_ids": list(user_ids),
            "agent_uuids": list(agent_uuids)
        }
    except Exception as e:
        return {"error": str(e)}, 500
    
#2nd Page

@app.route('/session')
@login_required
def session_redirect():
    session_id = request.args.get('session_id')
    if session_id:
        return redirect(url_for('session_view', session_id=session_id))
    return redirect(url_for('index'))

@app.route('/session/<session_id>')
@login_required
def session_view(session_id):
    try:
        print(f"\n--- Debug Info for Session {session_id} ---")
        # Fetch session_status summary
        session['clerk_token']= get_clerk_sign_token_for_user(session['user_id'])
        auth_token = session['clerk_token']
        headers = {"Authorization": f"Bearer {auth_token}"}
        status_summary_url = f"{API_BASE_URL}/v2/status/{session_id}"
        print(f"Fetching status_summary from: {status_summary_url}")
        status_summary_response = requests.get(status_summary_url,headers=headers)
        status_summary = status_summary_response.json()['session'] if status_summary_response.status_code == 200 else None

        # Fetch event stats
        session['clerk_token']= get_clerk_sign_token_for_user(session['user_id'])
        auth_token = session['clerk_token']
        headers = {"Authorization": f"Bearer {auth_token}"}
        event_stats_url = f"{API_BASE_URL}/v2/session-stats/{session_id}"
        print(f"Fetching status_summary from: {event_stats_url}")
        event_stats_response = requests.get(event_stats_url,headers=headers)
        event_stats = event_stats_response.json()['stats'] if event_stats_response.status_code == 200 else None
        
        # Fetch session summary
        session['clerk_token']= get_clerk_sign_token_for_user(session['user_id'])
        auth_token = session['clerk_token']
        headers = {"Authorization": f"Bearer {auth_token}"}
        summary_url = f"{API_BASE_URL}/v2/session_summary/{session_id}"
        print(f"Fetching summary from: {summary_url}")
        summary_response = requests.get(summary_url,headers=headers)
        summary = summary_response.json()['summary'] if summary_response.status_code == 200 else None
        
        # Get filter parameters using correct field name
        subagent_id = request.args.get('subagent_id')  # This stays the same as it's the parameter name
        event_type = request.args.get('event_type')
        
        # Fetch subagents (endpoint now returns correct subagent_id)
        session['clerk_token']= get_clerk_sign_token_for_user(session['user_id'])
        auth_token = session['clerk_token']
        headers = {"Authorization": f"Bearer {auth_token}"}
        subagents_url = f"{API_BASE_URL}/v2/subagents/{session_id}"
        print(f"Fetching subagents from: {subagents_url}")
        subagents_response = requests.get(subagents_url,headers=headers)
        subagents = subagents_response.json()['subagents'] if subagents_response.status_code == 200 else []

        # Fetch subagent statistics
        session['clerk_token']= get_clerk_sign_token_for_user(session['user_id'])
        auth_token = session['clerk_token']
        headers = {"Authorization": f"Bearer {auth_token}"}
        subagent_stats_url = f"{API_BASE_URL}/v2/subagent-stats/{session_id}"
        print(f"Fetching subagent stats from: {subagent_stats_url}")
        subagent_stats_response = requests.get(subagent_stats_url,headers=headers)
        subagent_stats = subagent_stats_response.json().get('stats', []) if subagent_stats_response.status_code == 200 else []
        
        # Fetch events with correct subagent_id parameter
        events_url = f"{API_BASE_URL}/v2/events/{session_id}"
        params = {}
        if subagent_id:
            params['subagent_id'] = subagent_id  # This parameter name matches the API endpoint
        if event_type:
            params['event_type'] = event_type
            
        print(f"Fetching events from: {events_url}")
        session['clerk_token']= get_clerk_sign_token_for_user(session['user_id'])
        auth_token = session['clerk_token']
        headers = {"Authorization": f"Bearer {auth_token}"}
        print(f"With params: {params}")
        events_response = requests.get(events_url, params=params, headers=headers)
        events = events_response.json()['events'] if events_response.status_code == 200 else []
        
        # Get unique event types
        event_types = {event['event_type'] for event in events if event['event_type']}
        
        print("\nData being passed to template:")
        print(f"Summary: {summary}")
        print(f"Events Count: {len(events)}")
        print(f"Subagents Count: {len(subagents)}")
        print(f"Event Types: {event_types}")
        print(f"status_summary: {status_summary}")
        print(f"subagent_stats: {subagent_stats}")
        

        return render_template('session.html',
                             status_summary=status_summary,
                             subagent_stats=subagent_stats,
                             event_stats=event_stats,
                             summary=summary,
                             events=events,
                             session_id=session_id,
                             subagents=subagents,
                             event_types=event_types,
                             current_subagent=subagent_id,
                             current_event_type=event_type)
                             
    except requests.exceptions.ConnectionError:
        print("Connection Error: Could not connect to the API server")
        return "Error: Could not connect to the API server. Please make sure it's running.", 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return f"An unexpected error occurred: {str(e)}", 500


if __name__ == '__main__':
    app.run()