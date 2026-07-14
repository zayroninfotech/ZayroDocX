import pymongo
from django.conf import settings
from datetime import datetime

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        _client = pymongo.MongoClient(settings.MONGO_URI)
        _db = _client[settings.MONGO_DB_NAME]
    return _db


def save_job(tool_name, input_files, output_files, status='completed', meta=None):
    db = get_db()
    doc = {
        'tool': tool_name,
        'input_files': input_files,
        'output_files': output_files,
        'status': status,
        'meta': meta or {},
        'created_at': datetime.utcnow(),
    }
    result = db.jobs.insert_one(doc)
    return str(result.inserted_id)


def get_recent_jobs(limit=20):
    db = get_db()
    jobs = list(db.jobs.find({}, {'_id': 0}).sort('created_at', -1).limit(limit))
    return jobs


def get_stats():
    db = get_db()
    total = db.jobs.count_documents({})
    by_tool = list(db.jobs.aggregate([
        {'$group': {'_id': '$tool', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 10},
    ]))
    return {'total_jobs': total, 'by_tool': by_tool}
