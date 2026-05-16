from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from string import Template


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    version: str
    template: str


class PromptManager:
    """[反思2c-工程化] 文件化 prompt 管理器，支持版本号和变量模板。"""

    def __init__(self, prompt_dir: Path | None = None):
        self.prompt_dir = prompt_dir or Path(__file__).resolve().parent
        self._cache: dict[str, PromptTemplate] = {}

    def render(self, name: str, **kwargs) -> str:
        prompt = self.load(name)
        return Template(prompt.template).safe_substitute(**kwargs)

    def load(self, name: str) -> PromptTemplate:
        if name not in self._cache:
            self._cache[name] = self._load_yaml(name)
        return self._cache[name]

    def _load_yaml(self, name: str) -> PromptTemplate:
        path = self.prompt_dir / f"{name}.yaml"
        text = path.read_text(encoding="utf-8")
        version = "v0"
        template_lines: list[str] = []
        in_template = False

        for line in text.splitlines():
            if line.startswith("version:"):
                version = line.split(":", 1)[1].strip().strip('"')
                continue
            if line.startswith("template:"):
                in_template = True
                continue
            if in_template:
                template_lines.append(line[2:] if line.startswith("  ") else line)

        template = "\n".join(template_lines).strip()
        if not template:
            raise ValueError(f"Prompt template {name} is empty")
        return PromptTemplate(name=name, version=version, template=template)


prompt_manager = PromptManager()
