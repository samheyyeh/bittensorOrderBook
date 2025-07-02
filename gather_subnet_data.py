import os
import bittensor
import pandas as pd
from datetime import datetime
from app import app, db, SubnetEmission

# === SUBNETS TO TRACK ===
SUBNET_IDS = [3, 4, 8, 10, 5, 19, 56, 64]

def main():
    # === Timestamp and Bittensor Init ===
    timestamp = datetime.utcnow()
    subtensor = bittensor.subtensor()

    # === Collect Subnet Data ===
    all_data = []
    for subnet_id in SUBNET_IDS:
        metagraph = subtensor.metagraph(subnet_id)
        df = pd.DataFrame({
            "timestamp": [timestamp] * len(metagraph.uids),
            "date": [timestamp.date()] * len(metagraph.uids),
            "subnet_id": [subnet_id] * len(metagraph.uids),
            "uid": metagraph.uids.tolist(),
            "stake": metagraph.S.tolist(),
            "emission": metagraph.emission.tolist(),
            "rank": metagraph.R.tolist()
        })
        all_data.append(df)

    # === Combine All Subnet Data ===
    combined_df = pd.concat(all_data, ignore_index=True)

    # === Insert Data into Database ===
    inserted = 0
    for _, row in combined_df.iterrows():
        # Check for duplicate (same timestamp, subnet_id, uid)
        exists = SubnetEmission.query.filter_by(
            timestamp=row['timestamp'],
            subnet_id=row['subnet_id'],
            uid=row['uid']
        ).first()
        if not exists:
            emission = SubnetEmission(
                timestamp=row['timestamp'],
                date=row['date'],
                subnet_id=row['subnet_id'],
                uid=row['uid'],
                stake=row['stake'],
                emission=row['emission'],
                rank=row['rank']
            )
            db.session.add(emission)
            inserted += 1

    db.session.commit()
    print(f"✅ Inserted {inserted} new records for subnets {SUBNET_IDS} into the database.")

if __name__ == "__main__":
    with app.app_context():
        main() 