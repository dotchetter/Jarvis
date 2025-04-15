import functools
import pyttman

from jarvis.models import RAGMemory


# OpenAI RAG callbacks, connecting it to the database.
@functools.lru_cache(maxsize=256)
def mongo_get_memories(key: any):
    pyttman.logger.log(" - Getting memories from MongoDB")
    return [m.memory for m in RAGMemory.objects(author_key=str(key))]

def mongo_purge_all_memories(*_):
    for memory in RAGMemory.objects.all():
        memory.delete()

def mongo_purge_memories(key: any):
    for memory in RAGMemory.objects(author_key=key):
        memory.delete()

def mongo_append_memory(key: any, memory: str):
    RAGMemory(author_key=str(key), memory=memory).save()
    mongo_get_memories.cache_clear()
