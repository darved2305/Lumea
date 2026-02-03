"""
Test script for Phase 2 Memory Implementation (Mem0 + Graphiti)

Run from backend directory:
    python -m tests.test_phase2_memory
"""
import asyncio
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Load .env explicitly
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)

# Ensure GOOGLE_API_KEY is set (Graphiti/GenAI libraries might look for this)
gemini_key = os.environ.get("GEMINI_API_KEY")
if gemini_key and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = gemini_key
    print("Mapped GEMINI_API_KEY to GOOGLE_API_KEY for compatibility")

from app.services.memory_service import get_memory_service
from app.services.graph_service import get_graph_service

async def test_memory_service():
    """Test Mem0 memory service."""
    print("\n" + "="*60)
    print("TESTING MEMORY SERVICE (Mem0)")
    print("="*60)
    
    service = get_memory_service()
    test_user_id = "test-user-phase2-001"
    
    # Test 1: Add a memory
    print("\n1. Testing add memory...")
    try:
        # Note: Mem0 might also use LLM. If Ollama is configured, it uses that.
        result = await service.add(
            content="User prefers explanations in simple terms without medical jargon.",
            user_id=test_user_id,
            metadata={"type": "preference", "category": "communication"}
        )
        print(f"   ✓ Memory added: {result}")
    except Exception as e:
        print(f"   ✗ Error adding memory: {e}")
        # Continue testing other parts even if this fails
    
    # Test 2: Search memories
    print("\n2. Testing search memories...")
    try:
        results = await service.search(
            query="how does user like explanations",
            user_id=test_user_id,
            limit=5
        )
        print(f"   ✓ Search results: {len(results)} memories found")
    except Exception as e:
        print(f"   ✗ Error searching: {e}")
    
    # Clean up
    try:
        await service.delete_all(user_id=test_user_id)
        print(f"   ✓ Cleanup complete")
    except Exception as e:
        print(f"   ⚠ Cleanup failed: {e}")
    
    return True

async def test_graph_service():
    """Test Graphiti graph service."""
    print("\n" + "="*60)
    print("TESTING GRAPH SERVICE (Graphiti + Neo4j + Gemini)")
    print("="*60)
    
    service = get_graph_service()
    
    # Test 1: Initialize
    print("\n1. Testing initialize...")
    try:
        success = await service.initialize()
        if success and service.is_available:
            print(f"   ✓ Graph service initialized and available")
        else:
            print(f"   ✗ Graph service initialization failed")
            return False
            
    except Exception as e:
        print(f"   ✗ Error initializing: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Add episode
    print("\n2. Testing add episode (Text -> Graph)...")
    try:
        print("   Sending text to Gemini for extraction...")
        success = await service.add_episode(
            content="Patient test-user-001 has HbA1c of 7.2%, indicating prediabetic condition.",
            name="test_episode_001",
            source="text",
            source_description="test script verification"
        )
        if success:
            print(f"   ✓ Episode added to graph")
        else:
            print(f"   ✗ Failed to add episode")
            return False
    except Exception as e:
        print(f"   ✗ Error adding episode: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Search
    print("\n3. Testing search...")
    try:
        print("   Waiting for indexing...")
        await asyncio.sleep(2)
        print("   Searching...")
        results = await service.search("diabetes indicators")
        print(f"   ✓ Search results: {len(results)} facts found")
        for i, res in enumerate(results[:3]):
            print(f"      - Result {i+1}: {res.get('fact', 'N/A')}")
    except Exception as e:
        print(f"   ✗ Error searching: {e}")
        return False
    
    # Test 4: Close
    print("\n4. Testing close...")
    try:
        await service.close()
        print(f"   ✓ Closed connection")
    except Exception as e:
        print(f"   ✗ Error closing: {e}")
    
    return True

async def main():
    print("\n" + "#"*60)
    print("# PHASE 2 MEMORY IMPLEMENTATION TEST SUITE (E2E)")
    print("#"*60)
    
    print(f"Environment:")
    print(f" - GEMINI_API_KEY found: {bool(os.environ.get('GEMINI_API_KEY'))}")
    print(f" - GOOGLE_API_KEY found: {bool(os.environ.get('GOOGLE_API_KEY'))}")
    
    mem_ok = await test_memory_service()
    graph_ok = await test_graph_service()
    
    if mem_ok and graph_ok:
        print("\n✓ ALL TESTS COMPLETED")
    else:
        print("\n✗ SOME TESTS FAILED")

if __name__ == "__main__":
    asyncio.run(main())
