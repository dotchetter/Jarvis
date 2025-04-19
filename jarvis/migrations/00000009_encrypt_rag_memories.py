import os

from fernet import Fernet

from jarvis.abilities.recipes.models import Recipe

__doc__ = "Encrypt all memories in the database"

from jarvis.models import RAGMemory


def upgrade():
    fernet = Fernet(os.environ["DPKEY"].encode())
    for memory in RAGMemory.objects.all():
        memory_string = memory.memory
        encrypted_memory = fernet.encrypt(memory_string.encode("utf-8"))
        encrypted_memory = encrypted_memory.decode("utf-8")
        memory.memory = encrypted_memory
        memory.save()

def downgrade():
    fernet = Fernet(os.environ["DPKEY"].encode())
    for memory in RAGMemory.objects.all():
        memory_string = memory.memory
        decrypted_memory = fernet.decrypt(memory_string.encode("utf-8"))
        decrypted_memory = decrypted_memory.decode("utf-8")
        memory.memory = decrypted_memory
        memory.save()
