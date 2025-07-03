import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from models import db, SubnetEmission
from io import BytesIO

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
    records = SubnetEmission.query.all()
    if not records:
        print("No data in database.")
        return
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
    print("Plots generated in static/plots/")

def generate_all_subnet_charts(netuid):
    records = SubnetEmission.query.filter_by(subnet_id=netuid).all()
    if not records:
        return {}
    df = pd.DataFrame([r.to_dict() for r in records])
    df = df.sort_values("timestamp")
    subnet_name = subnet_names.get(netuid, f"Subnet {netuid}")
    plot_dir = os.path.join("static", "plots")
    os.makedirs(plot_dir, exist_ok=True)
    sns.set(style="whitegrid", context="talk")
    plots = {}

    # 1. Stake Over Time
    plt.figure(figsize=(14, 6))
    plt.plot(df["timestamp"], df["stake"], label="Stake", alpha=0.7)
    plt.title(f"Stake Over Time: {subnet_name}")
    plt.xlabel("Timestamp")
    plt.ylabel("Stake")
    plt.tight_layout()
    fname = f"stake_over_time_{netuid}.png"
    plt.savefig(os.path.join(plot_dir, fname))
    plt.close()
    plots["Stake Over Time"] = f"plots/{fname}"

    # 2. Emission vs Stake
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x="stake", y="emission", alpha=0.6)
    plt.title(f"Emission vs Stake: {subnet_name}")
    plt.xlabel("Stake")
    plt.ylabel("Emission")
    plt.tight_layout()
    fname = f"emission_vs_stake_{netuid}.png"
    plt.savefig(os.path.join(plot_dir, fname))
    plt.close()
    plots["Emission vs Stake"] = f"plots/{fname}"

    # 3. Weekly Emissions
    df.set_index("timestamp", inplace=True)
    weekly_emission = df["emission"].resample("W").sum().reset_index()
    plt.figure(figsize=(14, 6))
    sns.lineplot(data=weekly_emission, x="timestamp", y="emission", marker="o")
    plt.title(f"Weekly Emissions: {subnet_name}")
    plt.xlabel("Week")
    plt.ylabel("Total Emission")
    plt.tight_layout()
    fname = f"weekly_emissions_{netuid}.png"
    plt.savefig(os.path.join(plot_dir, fname))
    plt.close()
    plots["Weekly Emissions"] = f"plots/{fname}"
    df.reset_index(inplace=True)

    # 4. Emission vs Rank
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x="rank", y="emission", alpha=0.6)
    plt.title(f"Emission vs Rank: {subnet_name}")
    plt.xlabel("Rank")
    plt.ylabel("Emission")
    plt.tight_layout()
    fname = f"emission_vs_rank_{netuid}.png"
    plt.savefig(os.path.join(plot_dir, fname))
    plt.close()
    plots["Emission vs Rank"] = f"plots/{fname}"

    # 5. Subnet Efficiency (Emission per Stake)
    df["efficiency"] = df["emission"] / (df["stake"] + 1e-9)
    eff_df = df.groupby("uid")["efficiency"].mean().sort_values(ascending=False)
    plt.figure(figsize=(10, 6))
    sns.barplot(x=eff_df.values, y=eff_df.index, palette="magma")
    plt.title(f"Subnet Efficiency (Emission per Stake): {subnet_name}")
    plt.xlabel("Avg Efficiency")
    plt.ylabel("UID")
    plt.tight_layout()
    fname = f"subnet_efficiency_{netuid}.png"
    plt.savefig(os.path.join(plot_dir, fname))
    plt.close()
    plots["Subnet Efficiency (Emission per Stake)"] = f"plots/{fname}"

    # 6. Rank Distribution Histogram
    plt.figure(figsize=(10, 6))
    sns.histplot(data=df, x="rank", bins=50, element="step", stat="count", common_norm=False)
    plt.title(f"Rank Distribution: {subnet_name}")
    plt.xlabel("Rank")
    plt.ylabel("Count")
    plt.tight_layout()
    fname = f"rank_histogram_{netuid}.png"
    plt.savefig(os.path.join(plot_dir, fname))
    plt.close()
    plots["Rank Distribution Histogram"] = f"plots/{fname}"

    # 7. Subnet Growth Over Time (Unique UIDs)
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    uid_growth = df.groupby(["date"])["uid"].nunique().reset_index()
    plt.figure(figsize=(14, 6))
    sns.lineplot(data=uid_growth, x="date", y="uid", marker="o")
    plt.title(f"Subnet Growth Over Time (Unique UIDs): {subnet_name}")
    plt.xlabel("Date")
    plt.ylabel("Unique UIDs")
    plt.tight_layout()
    fname = f"uid_growth_{netuid}.png"
    plt.savefig(os.path.join(plot_dir, fname))
    plt.close()
    plots["Subnet Growth Over Time (Unique UIDs)"] = f"plots/{fname}"

    return plots

def generate_single_subnet_plot(netuid):
    records = SubnetEmission.query.filter_by(subnet_id=netuid).all()
    if not records:
        return None
    df = pd.DataFrame([r.to_dict() for r in records])
    df = df.sort_values("timestamp")
    subnet_name = subnet_names.get(netuid, f"Subnet {netuid}")
    plot_dir = os.path.join("static", "plots")
    os.makedirs(plot_dir, exist_ok=True)
    plot_path = os.path.join(plot_dir, f"emissions_{netuid}.png")
    sns.set(style="whitegrid", context="talk")
    plt.figure(figsize=(14, 6))
    plt.plot(df["timestamp"], df["emission"], label="Emission", alpha=0.7)
    plt.title(f"Emissions Over Time: {subnet_name}")
    plt.xlabel("Timestamp")
    plt.ylabel("Emission")
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()
    return f"plots/emissions_{netuid}.png"

def generate_plot_for_type(netuid, plot_type):
    records = SubnetEmission.query.filter_by(subnet_id=netuid).all()
    if not records:
        return None
    df = pd.DataFrame([r.to_dict() for r in records])
    df = df.sort_values("timestamp")
    subnet_name = subnet_names.get(netuid, f"Subnet {netuid}")
    sns.set(style="whitegrid", context="talk")
    buf = BytesIO()

    if plot_type == "stake_over_time":
        plt.figure(figsize=(14, 6))
        plt.plot(df["timestamp"], df["stake"], label="Stake", alpha=0.7)
        plt.title(f"Stake Over Time: {subnet_name}")
        plt.xlabel("Timestamp")
        plt.ylabel("Stake")
        plt.tight_layout()
    elif plot_type == "emission_vs_stake":
        plt.figure(figsize=(10, 6))
        sns.scatterplot(data=df, x="stake", y="emission", alpha=0.6)
        plt.title(f"Emission vs Stake: {subnet_name}")
        plt.xlabel("Stake")
        plt.ylabel("Emission")
        plt.tight_layout()
    elif plot_type == "weekly_emissions":
        df.set_index("timestamp", inplace=True)
        weekly_emission = df["emission"].resample("W").sum().reset_index()
        plt.figure(figsize=(14, 6))
        sns.lineplot(data=weekly_emission, x="timestamp", y="emission", marker="o")
        plt.title(f"Weekly Emissions: {subnet_name}")
        plt.xlabel("Week")
        plt.ylabel("Total Emission")
        plt.tight_layout()
        df.reset_index(inplace=True)
    elif plot_type == "emission_vs_rank":
        plt.figure(figsize=(10, 6))
        sns.scatterplot(data=df, x="rank", y="emission", alpha=0.6)
        plt.title(f"Emission vs Rank: {subnet_name}")
        plt.xlabel("Rank")
        plt.ylabel("Emission")
        plt.tight_layout()
    elif plot_type == "subnet_efficiency":
        df["efficiency"] = df["emission"] / (df["stake"] + 1e-9)
        eff_df = df.groupby("uid")["efficiency"].mean().sort_values(ascending=False)
        plt.figure(figsize=(10, 6))
        sns.barplot(x=eff_df.values, y=eff_df.index, palette="magma")
        plt.title(f"Subnet Efficiency (Emission per Stake): {subnet_name}")
        plt.xlabel("Avg Efficiency")
        plt.ylabel("UID")
        plt.tight_layout()
    elif plot_type == "rank_histogram":
        plt.figure(figsize=(10, 6))
        sns.histplot(data=df, x="rank", bins=50, element="step", stat="count", common_norm=False)
        plt.title(f"Rank Distribution: {subnet_name}")
        plt.xlabel("Rank")
        plt.ylabel("Count")
        plt.tight_layout()
    elif plot_type == "uid_growth":
        df["date"] = pd.to_datetime(df["timestamp"]).dt.date
        uid_growth = df.groupby(["date"])["uid"].nunique().reset_index()
        plt.figure(figsize=(14, 6))
        sns.lineplot(data=uid_growth, x="date", y="uid", marker="o")
        plt.title(f"Subnet Growth Over Time (Unique UIDs): {subnet_name}")
        plt.xlabel("Date")
        plt.ylabel("Unique UIDs")
        plt.tight_layout()
    else:
        return None
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return buf

if __name__ == "__main__":
    with app.app_context():
        generate_emission_plots() 