import json
from typing import Dict, Any, Tuple
from shadow.core.logging import logger

class Validator:
    @staticmethod
    def validate_html(content: str) -> Tuple[bool, str]:
        if not content:
            return False, "HTML content is empty."

        # Simple HTML5 parsing/structure validation
        lower = content.lower()
        if "<!doctype html" not in lower:
            logger.warning("Missing DOCTYPE declaration.")

        open_tags = ["<html>", "<body>"]
        close_tags = ["</html>", "</body>"]

        for ot, ct in zip(open_tags, close_tags):
            if ot not in lower:
                return False, f"Missing required opening tag: {ot}"
            if ct not in lower:
                return False, f"Missing required closing tag: {ct}"

        return True, "HTML validated successfully."

    @staticmethod
    def validate_python(content: str) -> Tuple[bool, str]:
        if not content:
            return False, "Python content is empty."

        # Strip markdown wrapper if present
        if content.startswith("```python"):
            content = content[len("```python"):].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        try:
            compile(content, "<string>", "exec")
            return True, "Python compilation verification passed."
        except SyntaxError as e:
            return False, f"Python syntax error on line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Failed Python compilation: {e}"

    @staticmethod
    def validate_json(content: str) -> Tuple[bool, str]:
        if not content:
            return False, "JSON content is empty."

        # Strip markdown wrapper if present
        if content.startswith("```json"):
            content = content[len("```json"):].strip()
        elif content.startswith("```"):
            content = content[3:].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        try:
            json.loads(content)
            return True, "JSON structure validation passed."
        except json.JSONDecodeError as e:
            return False, f"JSON decoding failed: {e.msg} at line {e.lineno}, col {e.colno}"

    @staticmethod
    def validate_markdown(content: str) -> Tuple[bool, str]:
        if not content:
            return False, "Markdown content is empty."

        # Check structure: must contain at least one heading
        if not any(line.strip().startswith("#") for line in content.split("\n")):
            return False, "Markdown has no structural headings (e.g., # title)."

        return True, "Markdown structure validated successfully."

    @classmethod
    def validate_artifact(cls, content: str, file_type: str) -> Tuple[bool, str]:
        file_type = file_type.lower()
        if file_type == "html":
            return cls.validate_html(content)
        elif file_type == "python" or file_type == "py":
            return cls.validate_python(content)
        elif file_type == "json":
            return cls.validate_json(content)
        elif file_type == "markdown" or file_type == "md":
            return cls.validate_markdown(content)
        return True, "Unknown artifact format. Validation bypassed safely."
