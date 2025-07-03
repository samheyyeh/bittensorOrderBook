from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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