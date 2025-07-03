#!/usr/bin/env python3

from flask import Flask, render_template, jsonify
import pandas as pd
import os
from flask_sqlalchemy import SQLAlchemy
from subnetFinancialData import fetch_financial_data
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db as firebase_db

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

if __name__ == '__main__':
    # Remove or comment out db.create_all() if not needed
    app.run(debug=True)
