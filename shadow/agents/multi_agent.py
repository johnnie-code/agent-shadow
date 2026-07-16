from typing import Dict, Any, List, Callable
from shadow.agents.base import Agent

# Define all 10 specialized agent systems explicitly

def get_planner_agent(provider_name: str = "mock") -> Agent:
    return Agent(
        name="PlannerAgent",
        role="Planner",
        prompt="Analyze long-term goals, create roadmaps, and break them down into structured tasks.",
        allowed_tools=["read_file", "write_file"],
        provider_name=provider_name
    )

def get_research_agent(provider_name: str = "mock") -> Agent:
    return Agent(
        name="ResearchAgent",
        role="Research",
        prompt="Execute targeted web research, compile news, check programming tutorials and study materials.",
        allowed_tools=["web_search", "http_request"],
        provider_name=provider_name
    )

def get_coding_agent(provider_name: str = "mock") -> Agent:
    return Agent(
        name="CodingAgent",
        role="Coding",
        prompt="Write pristine, production-grade source code, fix python bugs, and inspect file trees.",
        allowed_tools=["read_file", "write_file", "terminal_execute"],
        provider_name=provider_name
    )

def get_review_agent(provider_name: str = "mock") -> Agent:
    return Agent(
        name="ReviewAgent",
        role="Review",
        prompt="Audit code changes, check for security patterns, verify formatting, and enforce coding standards.",
        allowed_tools=["read_file", "git"],
        provider_name=provider_name
    )

def get_testing_agent(provider_name: str = "mock") -> Agent:
    return Agent(
        name="TestingAgent",
        role="Testing",
        prompt="Generate unit/integration tests and run test commands to verify code changes.",
        allowed_tools=["terminal_execute", "read_file", "write_file"],
        provider_name=provider_name
    )

def get_documentation_agent(provider_name: str = "mock") -> Agent:
    return Agent(
        name="DocumentationAgent",
        role="Documentation",
        prompt="Write clear README guides, architectural specifications, docstrings, and user manuals.",
        allowed_tools=["read_file", "write_file"],
        provider_name=provider_name
    )

def get_deployment_agent(provider_name: str = "mock") -> Agent:
    return Agent(
        name="DeploymentAgent",
        role="Deployment",
        prompt="Coordinate build pipelines, deployment triggers, and cloud services (Vercel, Supabase, etc.).",
        allowed_tools=["terminal_execute", "http_request"],
        provider_name=provider_name
    )

def get_learning_agent(provider_name: str = "mock") -> Agent:
    return Agent(
        name="LearningAgent",
        role="Learning",
        prompt="Formulate study plans, organize learning schedules, track reading goals, and review Kanji progress.",
        allowed_tools=["read_file", "write_file"],
        provider_name=provider_name
    )

def get_opportunity_agent(provider_name: str = "mock") -> Agent:
    return Agent(
        name="OpportunityAgent",
        role="Opportunity",
        prompt="Analyze trends and scanned data for remote jobs, scholarships, hackathons, and open source issues.",
        allowed_tools=["web_search", "http_request"],
        provider_name=provider_name
    )

def get_reflection_agent(provider_name: str = "mock") -> Agent:
    return Agent(
        name="ReflectionAgent",
        role="Reflection",
        prompt="Audit completed/failed tasks, calculate daily achievements, and strategy updates.",
        allowed_tools=["read_file", "write_file"],
        provider_name=provider_name
    )

# Dictionary map containing all 10 specialized agent roles
AGENT_MAP: Dict[str, Callable[[str], Agent]] = {
    "planner": get_planner_agent,
    "research": get_research_agent,
    "coding": get_coding_agent,
    "review": get_review_agent,
    "testing": get_testing_agent,
    "documentation": get_documentation_agent,
    "deployment": get_deployment_agent,
    "learning": get_learning_agent,
    "opportunity": get_opportunity_agent,
    "reflection": get_reflection_agent
}
