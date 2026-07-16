import os
import pytest
from shadow.core.database import init_db
from shadow.goals.reflection import reflection_engine
from shadow.agents.jules import jules_integration

@pytest.mark.asyncio
async def test_reflection_engine():
    init_db()
    reflection = await reflection_engine.perform_daily_reflection()
    assert "Error" not in reflection
    assert len(reflection) > 0

def test_jules_integration_workspace():
    res = jules_integration.prepare_jules_workspace(
        objective="Implement lightweight fast hash mapping",
        file_targets=["shadow/core/hash.py"],
        constraints="Fast startup, under 100 lines."
    )
    assert res["success"] is True
    assert os.path.exists(res["agents_file"])

    # Check contents
    with open(res["agents_file"], "r", encoding="utf-8") as f:
        content = f.read()
    assert "Fast startup, under 100 lines" in content

    # Cleanup
    if os.path.exists(res["agents_file"]):
        os.remove(res["agents_file"])

@pytest.mark.asyncio
async def test_jules_patch_verification():
    # Run simple echo verification command
    res = await jules_integration.apply_and_verify_patch(
        patch_content="diff dummy",
        test_command="echo 'Tests Pass!'"
    )
    assert res["success"] is True
    assert "Tests Pass!" in res["stdout"]
