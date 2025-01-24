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
        # Default invocation -> produces XML by default
        result = runner.invoke(cli, ["manabot"])
        assert result.exit_code == 0
        
        # Basic checks
        assert "README.md" in result.output
        assert "main.py" in result.output
        
        # New readme-specific checks in XML output
        # Make sure the README content goes in <instructions> and is flagged as <type>readme</type>
        assert "<type>readme</type>" in result.output
        assert "<instructions>" in result.output
        assert "# Manabot" in result.output  # Confirm the readme text is present

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
        
        # Confirm hierarchical readme content
        assert "# Root docs" in result.output
        assert "# Env docs" in result.output
        assert "sample.txt" in result.output
        
        # Also confirm they are recognized as readme in XML
        # You may check for readme markers multiple times if you want to ensure multiple READMEs are detected.
        assert result.output.count("<type>readme</type>") >= 2
        assert result.output.count("<instructions>") >= 2

def test_raw_format(monkeypatch):
    with tmp("src") as src:
        monkeypatch.setenv("CODE_CONTEXT_ROOT", str(src))
        create_test_codebase(src, {
            "manabot/manabot/main.py": "print('hello')",
        })
        
        runner = CliRunner()
        result = runner.invoke(cli, ["manabot", "-r"])
        assert result.exit_code == 0
        
        # Raw format should not have <documents> or XML tags
        assert "<documents>" not in result.output
        assert "main.py" in result.output

def test_raw_format_with_readme(monkeypatch):
    """Ensure readmes get the ### README START ### block in raw mode."""
    with tmp("src") as src:
        monkeypatch.setenv("CODE_CONTEXT_ROOT", str(src))
        create_test_codebase(src, {
            "manabot/README.md": "# Raw readme",
            "manabot/manabot/main.py": "print('hello')",
        })
        
        runner = CliRunner()
        result = runner.invoke(cli, ["manabot", "-r"])
        assert result.exit_code == 0
        
        # Check for the special readme markers
        assert "### README START ###" in result.output
        assert "### README END ###" in result.output
        # Confirm that the readme content is present inside those markers
        assert "# Raw readme" in result.output

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

def test_readme_prioritization(monkeypatch):
    """
    Test that READMEs appear first in output, properly ordered by directory depth.
    We test both XML and raw output formats to ensure READMEs are prioritized in both.
    
    Directory structure being tested:
        src/
            manabot/
                README.md           # Root README (should appear first)
                main.py
                env/
                    README.md       # Env README (should appear second)
                    config.py
                    data/
                        README.md   # Data README (should appear third)
                        types.py
    """
    with tmp("src") as src:
        monkeypatch.setenv("CODE_CONTEXT_ROOT", str(src))
        
        # Create a test codebase with multiple READMEs at different depths
        create_test_codebase(src, {
            # Root level README
            "manabot/README.md": "# Root level\nThis is the root README.",
            "manabot/main.py": "print('main')",
            
            # Env level README and file
            "manabot/env/README.md": "# Env level\nThis is the env README.",
            "manabot/env/config.py": "# Config file",
            
            # Data level README and file
            "manabot/env/data/README.md": "# Data level\nThis is the data README.",
            "manabot/env/data/types.py": "# Types file"
        })
        
        runner = CliRunner()
        
        # Part 1: Test XML output format
        result = runner.invoke(cli, ["manabot"])
        assert result.exit_code == 0

        # Track document indices to verify ordering
        readme_indices = []
        non_readme_indices = []
        lines = result.output.split('\n')
        current_index = None
        
        # Parse the XML output to find document indices
        for line in lines:
            if '<document index="' in line:
                current_index = int(line.split('"')[1])
            elif '<type>readme</type>' in line:
                readme_indices.append(current_index)
            elif '<document_content>' in line and current_index is not None:
                non_readme_indices.append(current_index)
        
        # Verify all READMEs come before non-READMEs
        assert all(r < n for r in readme_indices for n in non_readme_indices), \
            "Not all READMEs appear before non-READMEs in XML output"
            
        # Track README paths to verify depth ordering
        readme_paths = []
        current_path = None
        for line in lines:
            if '<source>' in line:
                current_path = line.split('<source>')[1].split('</source>')[0]
            elif '<type>readme</type>' in line:
                readme_paths.append(current_path)
        
        # Verify order of READMEs by depth
        assert len(readme_paths) == 3, f"Expected 3 READMEs, found {len(readme_paths)}"
        assert "manabot/README.md" in readme_paths[0], "Root README should be first"
        assert "manabot/env/README.md" in readme_paths[1], "Env README should be second"
        assert "manabot/env/data/README.md" in readme_paths[2], "Data README should be third"

        # Part 2: Test raw output format
        result = runner.invoke(cli, ["manabot", "-r"])
        assert result.exit_code == 0
        
        # Parse documents from raw format
        lines = result.output.split('\n')
        documents = []
        current_doc = None
        is_content = False

        for i, line in enumerate(lines):
            if line == "---":  # Start of new document or end of current
                if is_content:  # End of document
                    is_content = False
                    if current_doc:
                        documents.append(current_doc)
                        current_doc = None
                else:  # Start of document
                    is_content = True
                    if i > 0:
                        file_path = lines[i-1].strip()
                        if file_path:  # Only create doc if we found a path
                            current_doc = {
                                'path': file_path,
                                'is_readme': False,
                                'position': len(documents)
                            }
            elif line == "### README START ###":
                if current_doc:
                    current_doc['is_readme'] = True

        if current_doc:  # Add final document if exists
            documents.append(current_doc)

        # Verify we have the right number of documents
        assert len(documents) > 0, "No documents found in raw output"
        
        # Get positions of READMEs and non-READMEs
        readme_positions = [doc['position'] for doc in documents if doc['is_readme']]
        non_readme_positions = [doc['position'] for doc in documents if not doc['is_readme']]
        
        # Verify all READMEs come before non-READMEs
        assert len(readme_positions) == 3, f"Expected 3 READMEs in raw output, found {len(readme_positions)}"
        assert all(r < n for r in readme_positions for n in non_readme_positions), \
            "Found non-README files before all READMEs in raw output"

        # Get README paths in order and verify order by depth
        readme_docs = [doc for doc in documents if doc['is_readme']]
        assert "manabot/README.md" in readme_docs[0]['path'], "Root README should be first in raw output"
        assert "manabot/env/README.md" in readme_docs[1]['path'], "Env README should be second in raw output"
        assert "manabot/env/data/README.md" in readme_docs[2]['path'], "Data README should be third in raw output"
