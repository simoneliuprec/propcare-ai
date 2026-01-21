class FakeInsertResult:
    def __init__(self, data):
        self.data = data

class FakeTable:
    def __init__(self, store):
        self.store = store

    def insert(self, payload):
        # emulate Supabase insert; generate ID
        new_id = len(self.store) + 1
        row = {"id": new_id, **payload}
        self.store.append(row)
        return self

    def execute(self):
        # return last inserted row like supabase-py does
        return FakeInsertResult([self.store[-1]])

class FakeSupabase:
    def __init__(self):
        self.rows = []

    def table(self, name: str):
        assert name == "tickets"
        return FakeTable(self.rows)
