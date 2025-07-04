#!/usr/bin/env python3
import os
import base64

# Decode firebase_key.json from environment variable if present
if os.environ.get('FIREBASE_KEY_BASE64'):
    with open('firebase_key.json', 'wb') as f:
        f.write(base64.b64decode(os.environ['FIREBASE_KEY_BASE64']))

from datetime import datetime
import bittensor
import firebase_admin
from firebase_admin import credentials, db as firebase_db
import re

# Initialize Firebase
cred = credentials.Certificate('firebase_key.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://bittensor-data-dashboard-default-rtdb.firebaseio.com/'
})

PRIMARY_SUBNETS = [3, 4, 8, 10]
SECONDARY_SUBNETS = [5, 19, 56, 64]
ALL_SUBNETS = PRIMARY_SUBNETS + SECONDARY_SUBNETS

def main():
    subtensor = bittensor.subtensor()
    timestamp = datetime.utcnow().isoformat()
    safe_timestamp = re.sub(r'[^a-zA-Z0-9_-]', '-', timestamp)
    for subnet_id in ALL_SUBNETS:
        metagraph = subtensor.metagraph(subnet_id)
        for i, uid in enumerate(metagraph.uids.tolist()):
            record = {
                'timestamp': timestamp,
                'date': timestamp[:10],
                'subnet_id': subnet_id,
                'uid': int(uid),
                'stake': float(metagraph.S[i]),
                'emission': float(metagraph.emission[i]),
                'rank': float(metagraph.R[i])
            }
            key = f"{safe_timestamp}_{subnet_id}_{uid}"
            firebase_db.reference(f'subnet_logs/{key}').set(record)
    print('✅ Data written to Firebase Realtime Database')

if __name__ == '__main__':
    main() 