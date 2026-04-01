from typing import Optional, List

class Document:
    def __init__(self, title: str, content: str):
        self.title = title
        self.content = content

class ChatSession:
    def __init__(self, user_id: int, documents: Optional[List[Document]] = None):
        self.user_id = user_id
        self.documents = documents if documents is not None else []

