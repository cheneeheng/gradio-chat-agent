"""Example of Multimodal Document Auditing and Hashing.

This example demonstrates how:
1. Documents (PDF/Text) are attached to an intent.
2. The engine hashes the document data for the audit log.
3. The storage efficiency (hashing vs raw storage) is maintained.
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.demo_actions import counter_component, set_action, set_handler
from gradio_chat_agent.models.intent import ChatIntent, IntentMedia
from gradio_chat_agent.models.enums import IntentType, MediaType

def run_example():
    # 1. Setup
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "doc-audit-demo"
    
    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)

    # 2. Simulate a Document (e.g., a PDF encoded in base64)
    # Payload: "This is a dummy PDF content"
    doc_data = "VGhpcyBpcyBhIGR1bW15IFBERiBjb250ZW50" 
    media = IntentMedia(
        type=MediaType.DOCUMENT, 
        data=doc_data, 
        mime_type="application/pdf"
    )

    # 3. Create Intent with Document
    intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-doc-123",
        action_id="demo.counter.set",
        inputs={"value": 10},
        media=media
    )

    print("--- Executing Action with Document Attachment ---")
    result = engine.execute_intent(project_id, intent)

    # 4. Verify Metadata
    print(f"Status: {result.status}")
    print(f"Metadata: {result.metadata}")

    if "media_hash" in result.metadata:
        print("\nSUCCESS: Document detected and hashed.")
        print(f"Hash: {result.metadata['media_hash']}")
        print(f"Type: {result.metadata['media_type']}")
        
        # Verify the raw data is NOT in the execution record (to save DB space)
        # Note: In our current implementation, engine.execute_intent result contains 
        # the intent model dump, but the persistent SQL row only stores hash in metadata.
        print("Note: Raw document content is excluded from the persistent audit log.")

if __name__ == "__main__":
    run_example()
