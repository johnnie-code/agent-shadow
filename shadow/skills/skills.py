from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class Skill(BaseModel):
    name: str
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    prompt: str
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    templates: Dict[str, str] = Field(default_factory=dict)
    version: str = "1.0.0"

class SkillsRegistry:
    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._load_default_skills()

    def register(self, skill: Skill):
        self._skills[skill.name] = skill

    def get_skill(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def list_skills(self) -> List[Skill]:
        return list(self._skills.values())

    def _load_default_skills(self):
        self.register(Skill(
            name="fix_python_bug",
            description="Inspect a failing test, trace imports, and fix the specific bug in code.",
            metadata={"domain": "Software Engineering", "language": "Python"},
            prompt="Analyze failing context and write patch to target filepath.",
            examples=[{"failing_test": "test_add_error", "fix": "add safe try/except block"}],
            templates={"instruction": "Failing Context:\n{context}\nPlease patch: {filepath}"},
            version="1.0.0"
        ))

        self.register(Skill(
            name="research_scholarship",
            description="Search, extract, and map requirements of international study scholarships.",
            metadata={"domain": "Education Research", "target": "Scholarships"},
            prompt="Analyze search queries and generate structured markdown requirement charts.",
            examples=[{"query": "MEXT Tokyo", "output": "Written to mext_ Tokyo.md"}],
            templates={"instruction": "Evaluate MEXT or JASSO rules for {query}."},
            version="1.0.0"
        ))

        self.register(Skill(
            name="analyze_repository",
            description="Walk through file trees, identify config options, and discover architectural modules.",
            metadata={"domain": "DevOps / Review", "scope": "Codebase Analysis"},
            prompt="Perform structural analysis on target folder directories.",
            examples=[{"dir": "core", "output": "Created core_review.md"}],
            templates={"instruction": "Analyze folder structure inside: {dir}"},
            version="1.0.0"
        ))

# Global Skills singleton
skills_registry = SkillsRegistry()
