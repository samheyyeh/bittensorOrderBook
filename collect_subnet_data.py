#!/usr/bin/env python3
import os
from datetime import datetime
import pandas as pd
import bittensor
from app import db, SubnetLog, app

# === Subnets to track ===
PRIMARY_SUBNETS = [3, 4, 8, 10]
SECONDARY_SUBNETS = [5, 19, 56, 64]
ALL_SUBNETS = PRIMARY_SUBNETS + SECONDARY_SUBNETS

def fetch_and_store_subnet_data():
    with app.app_context():
        print('DB URI:', app.config['SQLALCHEMY_DATABASE_URI'])
        print('Table name:', SubnetLog.__tablename__)
        subtensor = bittensor.subtensor()
        timestamp = datetime.utcnow()
        added = 0
        duplicates = 0
        for subnet_id in ALL_SUBNETS:
            metagraph = subtensor.metagraph(subnet_id)
            for i, uid in enumerate(metagraph.uids.tolist()):
                exists = SubnetLog.query.filter_by(timestamp=timestamp, subnet_id=subnet_id, uid=uid).first()
                if not exists:
                    log = SubnetLog(
                        timestamp=timestamp,
                        date=timestamp.date(),
                        subnet_id=subnet_id,
                        uid=uid,
                        stake=float(metagraph.S[i]),
                        emission=float(metagraph.emission[i]),
                        rank=float(metagraph.R[i])
                    )
                    db.session.add(log)
                    added += 1
                    print(f"Adding: subnet_id={subnet_id}, uid={uid}")
                else:
                    duplicates += 1
                    print(f"Duplicate found: subnet_id={subnet_id}, uid={uid}")
        db.session.commit()
        print(f"✅ Logged data for subnets {ALL_SUBNETS} at {timestamp}")
        print(f"Total added: {added}, duplicates skipped: {duplicates}")

if __name__ == "__main__":
    fetch_and_store_subnet_data() 