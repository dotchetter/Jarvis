import functools
import os

import pyttman
from fernet import Fernet

from jarvis.models import RAGMemory


# OpenAI RAG callbacks, connecting it to the database.
@functools.lru_cache(maxsize=256)
def mongo_get_memories(key: any):
    """
    Get all memories from MongoDB for a given key.
    The memory content is decrypted before returning.
    """
    pyttman.logger.log(" - Getting memories from MongoDB")
    fernet = Fernet(os.environ["DPKEY"].encode())
    return [
        fernet.decrypt(memory.memory.encode("utf-8")).decode("utf-8")
        for memory in RAGMemory.objects(author_key=str(key))
    ]

def mongo_add_memory(key: any, memory: str):
    """
    Store a new memory in MongoDB. The memory content is encrypted.
    """
    fernet = Fernet(os.environ["DPKEY"].encode())
    encrypted_memory = fernet.encrypt(memory.encode("utf-8"))
    encrypted_memory = encrypted_memory.decode("utf-8")
    RAGMemory(author_key=str(key), memory=encrypted_memory).save()
    mongo_get_memories.cache_clear()

def mongo_purge_all_memories(*_):
    for memory in RAGMemory.objects.all():
        memory.delete()

def mongo_purge_memories(key: any):
    for memory in RAGMemory.objects(author_key=key):
        memory.delete()
