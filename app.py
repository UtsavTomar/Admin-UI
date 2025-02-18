from flask import Flask, render_template, request, redirect, url_for
import requests
from datetime import datetime
import os

app = Flask(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sessions/<time_filter>')
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

        response = requests.get(f"{API_BASE_URL}/v2/sessions", params=params)
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
def get_filter_options(time_filter):
    try:
        response = requests.get(f"{API_BASE_URL}/v2/sessions", params={"time_filter": time_filter})
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
def session_redirect():
    session_id = request.args.get('session_id')
    if session_id:
        return redirect(url_for('session_view', session_id=session_id))
    return redirect(url_for('index'))

@app.route('/session/<session_id>')
def session_view(session_id):
    try:
        print(f"\n--- Debug Info for Session {session_id} ---")
        # Fetch session_status summary
        status_summary_url = f"{API_BASE_URL}/v2/session/{session_id}"
        print(f"Fetching status_summary from: {status_summary_url}")
        status_summary_response = requests.get(status_summary_url)
        status_summary = status_summary_response.json()['session'] if status_summary_response.status_code == 200 else None
        
        # Fetch session summary
        summary_url = f"{API_BASE_URL}/v2/session_summary/{session_id}"
        print(f"Fetching summary from: {summary_url}")
        summary_response = requests.get(summary_url)
        summary = summary_response.json()['summary'] if summary_response.status_code == 200 else None
        
        # Get filter parameters using correct field name
        subagent_id = request.args.get('subagent_id')  # This stays the same as it's the parameter name
        event_type = request.args.get('event_type')
        
        # Fetch subagents (endpoint now returns correct subagent_id)
        subagents_url = f"{API_BASE_URL}/v2/subagents/{session_id}"
        print(f"Fetching subagents from: {subagents_url}")
        subagents_response = requests.get(subagents_url)
        subagents = subagents_response.json()['subagents'] if subagents_response.status_code == 200 else []
        
        # Fetch events with correct subagent_id parameter
        events_url = f"{API_BASE_URL}/v2/events/{session_id}"
        params = {}
        if subagent_id:
            params['subagent_id'] = subagent_id  # This parameter name matches the API endpoint
        if event_type:
            params['event_type'] = event_type
            
        print(f"Fetching events from: {events_url}")
        print(f"With params: {params}")
        events_response = requests.get(events_url, params=params)
        events = events_response.json()['events'] if events_response.status_code == 200 else []
        
        # Get unique event types
        event_types = {event['event_type'] for event in events if event['event_type']}
        
        print("\nData being passed to template:")
        print(f"Summary: {summary}")
        print(f"Events Count: {len(events)}")
        print(f"Subagents Count: {len(subagents)}")
        print(f"Event Types: {event_types}")
        
        return render_template('session.html',
                             status_summary=status_summary,
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


def handler(event, context):
    return app(event, context)
