#!/usr/bin/env python3

from flask import Flask, render_template, jsonify
import pandas as pd
import os
from flask_sqlalchemy import SQLAlchemy
from subnetFinancialData import fetch_financial_data
import json
from datetime import datetime

app = Flask(__name__)

# Database configuration
# Patch for Heroku: convert 'postgres://' to 'postgresql://' for SQLAlchemy
if 'DATABASE_URL' in os.environ:
    uri = os.environ['DATABASE_URL']
    if uri.startswith('postgres://'):
        uri = uri.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = uri
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///subnet_emissions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

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

@app.route('/')
def home():
    return render_template('index.html', subnets=subnet_names)

@app.route('/subnet/<int:netuid>')
def subnet_detail(netuid):
    # Fetch financial data for this subnet
    data = fetch_financial_data(netuid)
    subnet_name = subnet_names.get(netuid, f"Subnet {netuid}")
    return render_template('subnetDetail.html', data=data, subnet_name=subnet_name)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
