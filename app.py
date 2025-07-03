#!/usr/bin/env python3

from flask import Flask, render_template, jsonify
import pandas as pd
import os
from flask_sqlalchemy import SQLAlchemy
from subnetFinancialData import get_cached_financial_data
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for server
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
from datetime import datetime, timedelta

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

db = SQLAlchemy(app)

class SubnetEmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    date = db.Column(db.Date, nullable=False)
    subnet_id = db.Column(db.Integer, nullable=False)
    uid = db.Column(db.Integer, nullable=False)
    stake = db.Column(db.Float, nullable=False)
    emission = db.Column(db.Float, nullable=False)
    rank = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'date': self.date,
            'subnet_id': self.subnet_id,
            'uid': self.uid,
            'stake': self.stake,
            'emission': self.emission,
            'rank': self.rank
        }

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

PLOT_FILENAMES = [
    "stake_over_time.png",
    "emission_vs_stake.png",
    "weekly_emissions.png",
    "emission_vs_rank.png",
    "subnet_efficiency.png",
    "rank_histogram.png",
    "uid_growth.png"
]

def generate_emission_plots():
    # Query all data
    records = SubnetEmission.query.all()
    if not records:
        return []
    df = pd.DataFrame([r.to_dict() for r in records])
    df["subnet_name"] = df["subnet_id"].map(subnet_names).fillna("Other")
    df = df.sort_values("timestamp")
    plot_dir = os.path.join("static", "plots")
    os.makedirs(plot_dir, exist_ok=True)
    sns.set(style="whitegrid", context="talk")

    # 1. Stake Over Time by Subnet
    plt.figure(figsize=(14, 6))
    for name, group in df.groupby("subnet_name"):
        plt.plot(group["timestamp"], group["stake"], label=name, alpha=0.7)
    plt.title("Stake Over Time by Subnet")
    plt.xlabel("Timestamp")
    plt.ylabel("Stake")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, PLOT_FILENAMES[0]))
    plt.close()

    # 2. Emission vs Stake Scatter by Subnet
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x="stake", y="emission", hue="subnet_name", alpha=0.6)
    plt.title("Emission vs Stake")
    plt.xlabel("Stake")
    plt.ylabel("Emission")
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, PLOT_FILENAMES[1]))
    plt.close()

    # 3. Top Subnets by Weekly Emissions
    weekly_emission = df.set_index("timestamp").groupby("subnet_name")["emission"].resample("W").sum().reset_index()
    plt.figure(figsize=(14, 6))
    sns.lineplot(data=weekly_emission, x="timestamp", y="emission", hue="subnet_name", marker="o")
    plt.title("Weekly Emissions by Subnet")
    plt.xlabel("Week")
    plt.ylabel("Total Emission")
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, PLOT_FILENAMES[2]))
    plt.close()

    # 4. Emission vs Rank Pareto Curve
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x="rank", y="emission", hue="subnet_name", alpha=0.6)
    plt.title("Emission vs Rank (Pareto View)")
    plt.xlabel("Rank")
    plt.ylabel("Emission")
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, PLOT_FILENAMES[3]))
    plt.close()

    # 5. Subnet Efficiency (Emission per Stake)
    df["efficiency"] = df["emission"] / (df["stake"] + 1e-9)
    eff_df = df.groupby("subnet_name")["efficiency"].mean().sort_values(ascending=False)
    plt.figure(figsize=(10, 6))
    sns.barplot(x=eff_df.values, y=eff_df.index, palette="magma")
    plt.title("Subnet Efficiency (Emission per Stake)")
    plt.xlabel("Avg Efficiency")
    plt.ylabel("Subnet")
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, PLOT_FILENAMES[4]))
    plt.close()

    # 6. Rank Distribution Histogram
    plt.figure(figsize=(10, 6))
    sns.histplot(data=df, x="rank", bins=50, hue="subnet_name", element="step", stat="count", common_norm=False, multiple="stack")
    plt.title("Rank Distribution by Subnet")
    plt.xlabel("Rank")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, PLOT_FILENAMES[5]))
    plt.close()

    # 7. Subnet Growth Over Time (Unique UIDs)
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    uid_growth = df.groupby(["subnet_name", "date"])["uid"].nunique().reset_index()
    plt.figure(figsize=(14, 6))
    sns.lineplot(data=uid_growth, x="date", y="uid", hue="subnet_name", marker="o")
    plt.title("Subnet Growth Over Time (Unique UIDs)")
    plt.xlabel("Date")
    plt.ylabel("Unique UIDs")
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, PLOT_FILENAMES[6]))
    plt.close()

    return [f"plots/{fname}" for fname in PLOT_FILENAMES]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/financial')
def financial_dashboard():
    data = get_cached_financial_data()
    return render_template('subnetFinancialData.html', data=data)

@app.route('/emissions')
def emissions_dashboard():
    plot_paths = generate_emission_plots()
    plot_titles = [
        'Stake Over Time by Subnet',
        'Emission vs Stake Scatter by Subnet',
        'Weekly Emissions by Subnet',
        'Emission vs Rank (Pareto View)',
        'Subnet Efficiency (Emission per Stake)',
        'Rank Distribution by Subnet',
        'Subnet Growth Over Time (Unique UIDs)'
    ]
    plots = list(zip(plot_paths, plot_titles))
    return render_template('subnetEmissionsData.html', plots=plots)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
