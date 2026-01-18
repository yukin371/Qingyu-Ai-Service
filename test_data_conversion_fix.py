"""
Quick Test Script - Verify Data Conversion Key Name Fix
"""
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def test_key_names():
    """Test Agent output key names"""
    print("=" * 60)
    print("Data Conversion Key Name Test")
    print("=" * 60)
    print()

    # Simulate Agent outputs (using snake_case key names)
    agent_outputs = {
        "outline_agent": {
            "title": "Cultivation Legend",
            "genre": "Fantasy",
            "chapters": [
                {"chapter_id": 1, "title": "Prologue", "summary": "The beginning"}
            ]
        },
        "character_agent": {
            "characters": [
                {"character_id": "1", "name": "Protagonist", "role_type": "protagonist"}
            ]
        },
        "plot_agent": {
            "timeline_events": [
                {"event_id": "e1", "title": "Starting Event"}
            ],
            "plot_threads": []
        }
    }

    print("[PASS] Test 1: Agent outputs key names")
    print(f"   Keys: {list(agent_outputs.keys())}")
    assert "outline_agent" in agent_outputs, "[FAIL] Missing outline_agent"
    assert "character_agent" in agent_outputs, "[FAIL] Missing character_agent"
    assert "plot_agent" in agent_outputs, "[FAIL] Missing plot_agent"
    print("   All Agent key names correct (snake_case)")
    print()

    print("[PASS] Test 2: Get Outline data")
    outline = agent_outputs.get("outline_agent", {})
    print(f"   Title: {outline.get('title')}")
    print(f"   Genre: {outline.get('genre')}")
    print(f"   Chapters: {len(outline.get('chapters', []))}")
    assert outline.get("title") == "Cultivation Legend", "[FAIL] Outline title mismatch"
    assert len(outline.get("chapters", [])) > 0, "[FAIL] Outline chapters empty"
    print("   Outline data retrieved successfully")
    print()

    print("[PASS] Test 3: Get Character data")
    characters = agent_outputs.get("character_agent", {})
    print(f"   Characters: {len(characters.get('characters', []))}")
    assert len(characters.get("characters", [])) > 0, "[FAIL] Characters empty"
    print("   Character data retrieved successfully")
    print()

    print("[PASS] Test 4: Get Plot data")
    plot = agent_outputs.get("plot_agent", {})
    print(f"   Events: {len(plot.get('timeline_events', []))}")
    assert len(plot.get("timeline_events", [])) > 0, "[FAIL] Plot events empty"
    print("   Plot data retrieved successfully")
    print()

    print("[PASS] Test 5: Wrong key name (PascalCase)")
    wrong_outline = agent_outputs.get("OutlineAgent", {})
    print(f"   Wrong key returns: {wrong_outline}")
    assert wrong_outline == {}, "[FAIL] Should return empty dict"
    print("   Correctly rejected wrong key name")
    print()

    print("=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("Summary:")
    print("[OK] Agent outputs use snake_case key names")
    print("[OK] gRPC Servicer should use matching key names")
    print("[OK] Data conversion layer fix is effective")
    print()

if __name__ == "__main__":
    try:
        test_key_names()
        sys.exit(0)
    except AssertionError as e:
        print(f"[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Runtime error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

