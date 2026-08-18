import os
import json
import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from backend.app.config.config import settings

class MockMongoCollection:
    def __init__(self, file_path: str, collection_name: str):
        self.file_path = file_path
        self.collection_name = collection_name
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump({}, f)

    def _read_data(self):
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_data(self, data):
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=4)

    def insert_one(self, document: dict):
        data = self._read_data()
        if self.collection_name not in data:
            data[self.collection_name] = []
        
        # Ensure _id field
        if "_id" not in document:
            document["_id"] = str(len(data[self.collection_name]) + 1)
        
        data[self.collection_name].append(document)
        self._write_data(data)
        return document

    def find_one(self, filter_dict: dict):
        data = self._read_data()
        collection = data.get(self.collection_name, [])
        for doc in collection:
            match = True
            for k, v in filter_dict.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                return doc
        return None

    def find(self, filter_dict: dict = None):
        data = self._read_data()
        collection = data.get(self.collection_name, [])
        if not filter_dict:
            return collection
        
        results = []
        for doc in collection:
            match = True
            for k, v in filter_dict.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                results.append(doc)
        return results

class MongoDatabase:
    def __init__(self):
        self.client = None
        self.db = None
        self.use_mock = False
        self.mock_file = "aetheria_mongo_mock.json"
        
        try:
            # Short timeout to fail quickly if database server isn't running
            self.client = pymongo.MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=2000)
            self.client.server_info()  # Forces connection check
            self.db = self.client[settings.MONGODB_DB_NAME]
            self.use_mock = False
        except (ConnectionFailure, ServerSelectionTimeoutError):
            print("MongoDB not reachable. Falling back to local JSON-backed mock database.")
            self.use_mock = True

    def get_collection(self, name: str):
        if self.use_mock:
            return MockMongoCollection(self.mock_file, name)
        return self.db[name]

mongo_db = MongoDatabase()
