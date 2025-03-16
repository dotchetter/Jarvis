from jarvis.models import RAGMemory


# OpenAI RAG callbacks, connecting it to the database.

def mongo_purge_all_memories(*_):
    for memory in RAGMemory.objects.all():
        memory.delete()

def mongo_purge_memories(key: any):
    for memory in RAGMemory.objects(author_key=key):
        memory.delete()

def mongo_append_memory(key: any, memory: str):
    memory = RAGMemory(author_key=str(key), memory=memory).save()
    print("Created memory:", memory)

def mongo_get_memories(key: any):
    return [m.memory for m in RAGMemory.objects(author_key=str(key))]
