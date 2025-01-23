import shutil
from contextlib import contextmanager
from pathlib import Path
from click.testing import CliRunner
from code_context.cli import cli
from typing import Iterator, Optional

TEST_ROOT = Path("/tmp/code_context_test")

@contextmanager
def tmp(name: str = "tmp", root: Optional[Path] = None) -> Iterator[Path]:
    """Creates a test project structure and cleans up after test completion."""
    root = root or TEST_ROOT
    project_path = root / name
    
    try:
        project_path.mkdir(parents=True, exist_ok=True)
        yield project_path
    finally:
        if project_path.exists():
            shutil.rmtree(project_path)

def create_test_codebase(root: Path, files: dict[str, str]) -> None:
    """Creates files with content in the test codebase."""
    for path, content in files.items():
        file_path = root / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

def test_basic_usage(monkeypatch):
    with tmp("src") as src:
        monkeypatch.setenv("CODE_CONTEXT_ROOT", str(src))
        create_test_codebase(src, {
            "manabot/manabot/main.py": "print('hello')",
            "manabot/README.md": "# Manabot"
        })
        
        runner = CliRunner()
        result = runner.invoke(cli, ["manabot"])
        assert result.exit_code == 0
        assert "README.md" in result.output
        assert "main.py" in result.output

def test_multiple_paths(monkeypatch):
    with tmp("src") as src:
        monkeypatch.setenv("CODE_CONTEXT_ROOT", str(src))
        create_test_codebase(src, {
            "manabot/manabot/main.py": "print('manabot')",
            "managym/tests/test_env.py": "def test_env(): pass",
        })
        
        runner = CliRunner()
        result = runner.invoke(cli, ["manabot,managym/tests"])
        assert result.exit_code == 0
        assert "main.py" in result.output
        assert "test_env.py" in result.output

def test_extension_filtering(monkeypatch):
    with tmp("src") as src:
        monkeypatch.setenv("CODE_CONTEXT_ROOT", str(src))
        create_test_codebase(src, {
            "manabot/manabot/main.py": "print('hello')",
            "manabot/manabot/config.js": "const config = {};",
            "manabot/README.md": "# Manabot"
        })
        
        runner = CliRunner()
        result = runner.invoke(cli, ["manabot", "-e", ".py"])
        assert result.exit_code == 0
        assert "main.py" in result.output
        assert "config.js" not in result.output

def test_hierarchical_readme(monkeypatch):
    with tmp("src") as src:
        monkeypatch.setenv("CODE_CONTEXT_ROOT", str(src))
        create_test_codebase(src, {
            "manabot/manabot/env/data/sample.txt": "data",
            "manabot/manabot/env/README.md": "# Env docs",
            "manabot/README.md": "# Root docs"
        })
        
        runner = CliRunner()
        result = runner.invoke(cli, ["manabot/env/data"])
        assert result.exit_code == 0
        assert "# Root docs" in result.output
        assert "# Env docs" in result.output
        assert "sample.txt" in result.output

def test_raw_format(monkeypatch):
    with tmp("src") as src:
        monkeypatch.setenv("CODE_CONTEXT_ROOT", str(src))
        create_test_codebase(src, {
            "manabot/manabot/main.py": "print('hello')",
        })
        
        runner = CliRunner()
        result = runner.invoke(cli, ["manabot", "-r"])
        assert result.exit_code == 0
        assert "<documents>" not in result.output
        assert "main.py" in result.output

def test_direct_path_resolution(monkeypatch):
    """Tests that direct paths work without requiring auto-prefixing."""
    with tmp("src") as src:
        monkeypatch.setenv("CODE_CONTEXT_ROOT", str(src))
        create_test_codebase(src, {
            "manabot/env/config.py": "settings = {}",
            "manabot/README.md": "# Direct Structure"
        })
        
        runner = CliRunner()
        result = runner.invoke(cli, ["manabot/env"])
        assert result.exit_code == 0
        assert "config.py" in result.output
        assert "# Direct Structure" in result.output

def test_auto_prefixed_path_resolution(monkeypatch):
    """Tests that auto-prefixing works when direct path doesn't exist."""
    with tmp("src") as src:
        monkeypatch.setenv("CODE_CONTEXT_ROOT", str(src))
        create_test_codebase(src, {
            "manabot/manabot/env/config.py": "settings = {}",
            "manabot/README.md": "# Prefixed Structure"
        })
        
        runner = CliRunner()
        result = runner.invoke(cli, ["manabot/env"])
        assert result.exit_code == 0
        assert "config.py" in result.output
        assert "# Prefixed Structure" in result.output

def test_root_files_access(monkeypatch):
    """Tests access to files in the root codebase directory."""
    with tmp("src") as src:
        monkeypatch.setenv("CODE_CONTEXT_ROOT", str(src))
        create_test_codebase(src, {
            "manabot/README.md": "# Root README",
            "manabot/CMakeLists.txt": "cmake_config",
            "manabot/manabot/main.py": "print('main')"
        })
        
        runner = CliRunner()
        result = runner.invoke(cli, ["manabot"])
        assert result.exit_code == 0
        assert "# Root README" in result.output
        assert "cmake_config" in result.output
        assert "main.py" in result.output

def test_prefers_direct_over_prefixed(monkeypatch):
    """Tests that direct paths are preferred when both exist."""
    with tmp("src") as src:
        monkeypatch.setenv("CODE_CONTEXT_ROOT", str(src))
        create_test_codebase(src, {
            "manabot/env/direct.py": "direct = True",
            "manabot/manabot/env/prefixed.py": "prefixed = True"
        })
        
        runner = CliRunner()
        result = runner.invoke(cli, ["manabot/env"])
        assert result.exit_code == 0
        assert "direct.py" in result.output
        assert "prefixed.py" not in result.output