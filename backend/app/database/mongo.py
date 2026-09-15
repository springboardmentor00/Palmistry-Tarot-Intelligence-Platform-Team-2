from pymongo import MongoClient
from backend.app.config.config import settings


class MongoStore:
    """Optional document store for audit/analysis documents.

    PostgreSQL remains the source of truth. MongoDB is used only when reachable;
    failures are surfaced to callers instead of silently substituting unavailable data.
    """
    def __init__(self):
        self.client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=2000)
        self.db = self.client[settings.MONGODB_DB_NAME]

    def ping(self) -> bool:
        self.client.admin.command("ping")
        return True

    def get_collection(self, name: str):
        return self.db[name]


mongo_db = MongoStore()
