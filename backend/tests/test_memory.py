import pytest
from app.memory.conversation_memory import ConversationMemory

def test_conversation_memory():
    memory = ConversationMemory(max_history=5)
    
    memory.add_message("sess1", "user", "Hello")
    memory.add_message("sess1", "assistant", "Hi")
    
    hist = memory.get_history("sess1")
    assert len(hist) == 2
    assert hist[0]["role"] == "user"
    assert hist[1]["role"] == "assistant"
    
    # Test max history trimming
    for i in range(10):
        memory.add_message("sess1", "user", str(i))
        
    hist_after = memory.get_history("sess1")
    assert len(hist_after) == 5
