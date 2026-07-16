import pytest
from shadow.tools.registry import tool_registry
from shadow.agents.multi_agent import AGENT_MAP, get_research_agent
from shadow.skills.skills import skills_registry

@pytest.mark.asyncio
async def test_multi_agent_system():
    tool_registry.discover_tools()

    # 1. Verify we can load and construct all 10 specialized agents
    assert len(AGENT_MAP) == 10
    for name, builder in AGENT_MAP.items():
        agent_inst = builder(provider_name="mock")
        assert agent_inst.name is not None
        assert agent_inst.role is not None
        assert len(agent_inst.allowed_tools) >= 0

    # 2. Test one of the agents executing instructions
    agent = get_research_agent(provider_name="mock")
    assert agent.name == "ResearchAgent"
    assert "web_search" in agent.allowed_tools

    res = await agent.execute_instruction("Search for upcoming Tokyo AI hackathons")
    assert res["success"] is True
    assert "thought" in res or "response" in res

def test_skills_system():
    skill = skills_registry.get_skill("fix_python_bug")
    assert skill is not None
    assert skill.version == "1.0.0"
    assert "language" in skill.metadata
    assert len(skill.examples) > 0
    assert "instruction" in skill.templates
