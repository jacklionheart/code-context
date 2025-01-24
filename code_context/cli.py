import os
import subprocess
from pathlib import Path
from typing import List, Set, Optional, Tuple, Callable
from fnmatch import fnmatch

import click

def get_code_context_root() -> Path:
    """Return the root directory for code context, defaulting to ~/src."""
    return Path(os.getenv("CODE_CONTEXT_ROOT", str(Path.home() / "src")))

def find_readmes(path: Path) -> List[Path]:
    """
    Walk from `path` upward to `CODE_CONTEXT_ROOT`, collecting README.md files.
    Then add any top-level README.md if not already included.

    Sort so that "highest-level" (fewest path parts) comes first,
    and, at the same depth, alphabetical order by path name.
    """
    code_root = get_code_context_root()
    readmes: List[Path] = []

    # Traverse upward
    current = path
    while current != code_root and current != Path.home():
        readme_candidate = current / "README.md"
        if readme_candidate.exists():
            readmes.append(readme_candidate)
        current = current.parent

    # Optionally check for a README in code_root itself
    root_readme = code_root / "README.md"
    if root_readme.exists() and root_readme not in readmes:
        readmes.append(root_readme)

    # Sort so fewest path parts (highest up) appears first; ties => alphabetical
    readmes.sort(key=lambda p: (len(p.parts), str(p).lower()))
    return readmes

def resolve_codebase_path(path_str: str) -> Path:
    """
    Convert path string to an absolute path following codebase conventions:
      1) Root codebase directory (e.g., "myproj")
      2) Direct subpath ("myproj/env")
      3) Auto-prefixed ("myproj/env" -> "myproj/myproj/env")
    """
    parts = path_str.split('/')
    if not parts:
        raise click.BadArgumentUsage("Empty path provided")

    code_root = get_code_context_root()
    codebase = parts[0]
    subpath = parts[1:]

    if not subpath:
        # e.g. "manabot" => $CODE_CONTEXT_ROOT/manabot
        return code_root / codebase
    if len(subpath) == 1 and subpath[0] == "tests":
        # e.g. "manabot/tests"
        return code_root / codebase / "tests"

    direct_path = code_root / codebase / "/".join(subpath)
    if direct_path.exists():
        return direct_path

    # If direct doesn't exist, try auto-prefix
    if subpath and subpath[0] != codebase:
        prefixed_path = code_root / codebase / codebase / "/".join(subpath)
        if prefixed_path.exists():
            return prefixed_path

    return direct_path

def copy_to_clipboard(content: str) -> None:
    """
    If on macOS (with pbcopy), copy output to clipboard;
    otherwise skip with a warning.
    """
    try:
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(content.encode('utf-8'))
    except FileNotFoundError:
        click.echo("pbcopy not found - clipboard integration skipped", err=True)

def read_gitignore(path: str) -> List[str]:
    """Return lines from .gitignore for ignoring certain files/directories."""
    gitignore_path = os.path.join(path, ".gitignore")
    if os.path.isfile(gitignore_path):
        with open(gitignore_path, "r") as f:
            return [
                line.strip() for line in f
                if line.strip() and not line.startswith("#")
            ]
    return []

def should_ignore(path: str, gitignore_rules: List[str]) -> bool:
    """
    Check if `path` should be ignored according to .gitignore patterns 
    (naive: only matches filename or directory name).
    """
    fname = os.path.basename(path)
    for rule in gitignore_rules:
        if fnmatch(fname, rule):
            return True
        if os.path.isdir(path) and fnmatch(fname + "/", rule):
            return True
    return False

def process_files(
    path: str,
    writer: Callable[[str], None],
    gitignore_rules: List[str],
    xml_format: bool,
    processed_files: Set[str],
    extensions: Optional[Tuple[str, ...]] = None
) -> None:
    """
    Recursively process files/folders at `path`.
    - If `xml_format` is True => produce <document> tags.
    - If not => produce raw text with optional README markers.
    """
    def print_file(file_path: str, content: str, is_readme: bool) -> None:
        """Output either raw or XML, marking readmes appropriately."""
        if file_path in processed_files:
            return
        if extensions and not any(file_path.endswith(ext) for ext in extensions):
            return

        processed_files.add(file_path)

        if not xml_format:
            # Raw format
            writer(file_path)
            writer("---")
            if is_readme:
                writer("### README START ###")
            writer(content)
            if is_readme:
                writer("### README END ###")
            writer("")
            writer("---")
        else:
            # XML format
            doc_index = len(processed_files)
            writer(f'<document index="{doc_index}">')
            writer(f"<source>{file_path}</source>")
            if is_readme:
                writer("<type>readme</type>")
                writer("<instructions>")
                writer(content)
                writer("</instructions>")
            else:
                writer("<document_content>")
                writer(content)
                writer("</document_content>")
            writer("</document>")

    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                is_readme = path.endswith("README.md")
                print_file(path, f.read(), is_readme)
        except UnicodeDecodeError:
            click.echo(f"Warning: Skipping file {path} due to UnicodeDecodeError", err=True)
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            # Skip hidden
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files = [f for f in files if not f.startswith(".")]

            # Apply .gitignore
            dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), gitignore_rules)]
            files = [f for f in files if not should_ignore(os.path.join(root, f), gitignore_rules)]

            for file_name in sorted(files):
                file_path = os.path.join(root, file_name)
                try:
                    with open(file_path, "r") as f:
                        is_readme = (file_name == "README.md")
                        print_file(file_path, f.read(), is_readme)
                except UnicodeDecodeError:
                    click.echo(f"Warning: Skipping file {file_path} due to UnicodeDecodeError", err=True)

@click.command()
@click.argument('paths')
@click.option('-p', '--pbcopy', is_flag=True, help="Copy to clipboard (macOS only)")
@click.option('-r', '--raw', is_flag=True, help="Output in raw format instead of XML")
@click.option('-e', '--extension', multiple=True, help="File extensions to include (e.g. -e .py -e .js)")
def cli(paths: str, pbcopy: bool, raw: bool, extension: Tuple[str, ...]) -> None:
    """
    Provide codebase context to LLMs with smart defaults.
    - PATHS can be comma-separated. Example: "manabot,managym/tests"
    """
    processed_files: Set[str] = set()
    content: List[str] = []
    writer: Callable[[str], None] = lambda s: content.append(s)

    # XML container
    if not raw:
        writer("<documents>")

    for path_str in paths.split(','):
        path_str = path_str.strip()
        path_obj = resolve_codebase_path(path_str)
        if not path_obj.exists():
            click.echo(f"Warning: Path does not exist: {path_obj}", err=True)
            continue

        # 1) Include parent READMEs in top->down order
        for readme_path in find_readmes(path_obj):
            process_files(
                path=str(readme_path),
                writer=writer,
                gitignore_rules=[],  # typically do not .gitignore parent-level readmes
                xml_format=not raw,
                processed_files=processed_files,
                extensions=extension
            )

        # 2) Then include the actual path
        process_files(
            path=str(path_obj),
            writer=writer,
            gitignore_rules=read_gitignore(str(path_obj)),
            xml_format=not raw,
            processed_files=processed_files,
            extensions=extension
        )

    if not raw:
        writer("</documents>")

    output_content = "\n".join(content)

    if pbcopy:
        copy_to_clipboard(output_content)
    else:
        click.echo(output_content)

if __name__ == "__main__":
    cli()
