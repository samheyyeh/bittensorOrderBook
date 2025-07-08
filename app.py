#!/usr/bin/env python3

from flask import Flask, render_template, jsonify, request
import pandas as pd
import os
from flask_sqlalchemy import SQLAlchemy
from subnetFinancialData import fetch_financial_data
import json
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db as firebase_db
import base64
import openai

# Decode firebase_key.json from environment variable if present
if os.environ.get('FIREBASE_KEY_BASE64'):
    with open('firebase_key.json', 'wb') as f:
        f.write(base64.b64decode(os.environ['FIREBASE_KEY_BASE64']))

# Initialize Firebase (only once)
if not firebase_admin._apps:
    cred = credentials.Certificate('firebase_key.json')
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://bittensor-data-dashboard-default-rtdb.firebaseio.com/'
    })

app = Flask(__name__)

# Database configuration
# Patch for Heroku: convert 'postgres://' to 'postgresql://' fGor SQLAlchemy
if 'DATABASE_URL' in os.environ:
    uri = os.environ['DATABASE_URL']
    if uri.startswith('postgres://'):
        uri = uri.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = uri
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///subnet_emissions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Remove or comment out SubnetLog and db usage if not needed

subnet_names = {
    3: "Templar",
    4: "Targon",
    5: "OpenKaito",
    8: "Taoshi",
    10: "Sturdy",
    19: "Vision",
    56: "Gradient",
    64: "Chutes"
}

# Remove or comment out SubnetLog model and SQLAlchemy usage if not needed

@app.route('/')
def home():
    return render_template('index.html', subnets=subnet_names)

@app.route('/subnet/<int:netuid>')
def subnet_detail(netuid):
    # Fetch financial data for this subnet
    data = fetch_financial_data(netuid)
    subnet_name = subnet_names.get(netuid, f"Subnet {netuid}")
    return render_template('subnetDetail.html', data=data, subnet_name=subnet_name, netuid=netuid)

@app.route('/logs')
def show_logs():
    ref = firebase_db.reference('subnet_logs')
    all_logs = ref.get()
    if not all_logs:
        return 'No logs found.'
    # Sort by timestamp descending, get 10 most recent
    logs = sorted(all_logs.values(), key=lambda x: x['timestamp'], reverse=True)[:10]
    return '<br>'.join([str(log) for log in logs])

@app.route('/api/subnet_data/<int:netuid>')
def api_subnet_data(netuid):
    ref = firebase_db.reference('subnet_logs')
    all_logs = ref.get()
    if not all_logs:
        return jsonify([])
    # Filter for this subnet
    subnet_logs = [log for log in all_logs.values() if int(log['subnet_id']) == netuid]
    # Sort by timestamp
    subnet_logs.sort(key=lambda x: x['timestamp'])
    return jsonify(subnet_logs)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json()
    subnet_id = data.get('subnet_id')
    question = data.get('question')
    if not subnet_id or not question:
        return jsonify({'error': 'Missing subnet_id or question'}), 400

    # Fetch all logs from Firebase
    ref = firebase_db.reference('subnet_logs')
    all_logs = ref.get()
    if not all_logs:
        return jsonify({'error': 'No logs found'}), 404

    # Filter logs for this subnet and last 7 days
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    subnet_logs = [
        log for log in all_logs.values()
        if int(log.get('subnet_id', -1)) == int(subnet_id)
        and 'timestamp' in log
        and datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')) >= seven_days_ago
    ]
    if not subnet_logs:
        return jsonify({'error': 'No recent data for this subnet'}), 404

    # Fetch financial data for this subnet
    financial_data = fetch_financial_data(int(subnet_id))
    if financial_data and isinstance(financial_data, dict):
        financial_summary = '\n'.join([f"{k.replace('_', ' ').title()}: {v}" for k, v in financial_data.items() if k != 'error'])
    else:
        financial_summary = 'No financial data available.'

    # Summarize the logs for the prompt (showing only a few recent entries for brevity)
    subnet_logs.sort(key=lambda x: x['timestamp'], reverse=True)
    summary_lines = []
    for log in subnet_logs[:10]:
        summary_lines.append(
            f"Date: {log['date']}, UID: {log['uid']}, Stake: {log['stake']}, Emission: {log['emission']}, Rank: {log['rank']}"
        )
    logs_summary = '\n'.join(summary_lines)

    prompt = f"You are a helpful assistant for Bittensor subnet analytics. Here is the latest financial data for subnet {subnet_id}:\n{financial_summary}\n\nHere is recent log data for subnet {subnet_id}:\n{logs_summary}\n\nUser question: {question}\n\nAnswer in a clear, concise, and helpful way."

    # Call OpenAI GPT-4.1
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if not openai_api_key:
        return jsonify({'error': 'OpenAI API key not set'}), 500
    client = openai.OpenAI()
    try:
        completion = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for Bittensor subnet analytics."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = completion.choices[0].message.content
        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Remove or comment out db.create_all() if not needed
    print("FIREBASE_KEY_BASE64 present:", bool(os.environ.get('FIREBASE_KEY_BASE64')))
    print("firebase_key.json exists:", os.path.exists('firebase_key.json'))
    if os.path.exists('firebase_key.json'):
        print("firebase_key.json size:", os.path.getsize('firebase_key.json'))
    app.run(debug=True)
