import os
import subprocess
from pathlib import Path
from typing import List, Set, Optional, Tuple, Callable
from fnmatch import fnmatch

import click

def get_code_context_root() -> Path:
    return Path(os.getenv("CODE_CONTEXT_ROOT", str(Path.home() / "src")))

def find_readmes(path: Path) -> List[Path]:
    """Find all README.md files in path and its parents, without duplicates."""
    readmes: Set[Path] = set()  # Using set to prevent duplicates
    current = path
    code_root = get_code_context_root()
    while current != code_root and current != Path.home():
        readme = current / "README.md"
        if readme.exists():
            readmes.add(readme)
        current = current.parent
    return sorted(readmes)  # Sort to maintain consistent order

def resolve_codebase_path(path_str: str) -> Path:
    """Convert path string to absolute path following codebase conventions."""
    parts = path_str.split('/')
    if not parts:
        raise click.BadArgumentUsage("Empty path provided")
        
    code_root = get_code_context_root()
    codebase = parts[0]
    subpath = parts[1:]
    
    # Special cases that don't get auto-prefixed
    if len(subpath) == 0:  # Root codebase directory
        return code_root / codebase
    if len(subpath) == 1 and subpath[0] == "tests":  # Tests directory
        return code_root / codebase / "tests"
        
    # Auto-prefix other paths with codebase name
    if subpath and subpath[0] != codebase:
        subpath.insert(0, codebase)
        
    return code_root / codebase / "/".join(subpath)

def copy_to_clipboard(content: str) -> None:
    try:
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(content.encode('utf-8'))
    except FileNotFoundError:
        click.echo("pbcopy not found - clipboard integration skipped", err=True)

def read_gitignore(path: str) -> List[str]:
    gitignore_path = os.path.join(path, ".gitignore")
    if os.path.isfile(gitignore_path):
        with open(gitignore_path, "r") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return []

def should_ignore(path: str, gitignore_rules: List[str]) -> bool:
    for rule in gitignore_rules:
        if fnmatch(os.path.basename(path), rule):
            return True
        if os.path.isdir(path) and fnmatch(os.path.basename(path) + "/", rule):
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
    def print_file(file_path: str, content: str) -> None:
        if file_path in processed_files:
            return
            
        if extensions and not any(file_path.endswith(ext) for ext in extensions):
            return
            
        processed_files.add(file_path)
        
        if not xml_format:  # Raw format
            writer(file_path)
            writer("---")
            writer(content)
            writer("")
            writer("---")
        else:  # XML format
            writer(f'<document index="{len(processed_files)}">')
            writer("<source>" + file_path + "</source>")
            writer("<document_content>")
            writer(content)
            writer("</document_content>")
            writer("</document>")

    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                print_file(path, f.read())
        except UnicodeDecodeError:
            click.echo(f"Warning: Skipping file {path} due to UnicodeDecodeError", err=True)
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files = [f for f in files if not f.startswith(".")]
            
            dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), gitignore_rules)]
            files = [f for f in files if not should_ignore(os.path.join(root, f), gitignore_rules)]

            for file in sorted(files):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as f:
                        print_file(file_path, f.read())
                except UnicodeDecodeError:
                    click.echo(f"Warning: Skipping file {file_path} due to UnicodeDecodeError", err=True)

@click.command()
@click.argument('paths')
@click.option('-p', '--pbcopy', is_flag=True, help="Copy to clipboard (OSX only)")
@click.option('-r', '--raw', is_flag=True, help='Output in raw format instead of Claude XML')
@click.option('-e', '--extension', multiple=True, help='File extensions to include')
def cli(paths: str, pbcopy: bool, raw: bool, extension: Tuple[str, ...]) -> None:
    """Provide codebase context to LLMs with smart defaults."""
    processed_files: Set[str] = set()
    content: List[str] = []
    writer: Callable[[str], None] = lambda s: content.append(s)
    
    if not raw:
        writer("<documents>")
    
    for path_str in paths.split(','):
        path = resolve_codebase_path(path_str.strip())
        if not path.exists():
            click.echo(f"Warning: Path does not exist: {path}", err=True)
            continue
            
        for readme in find_readmes(path):
            process_files(str(readme), writer, [], not raw, processed_files, extension)
        
        process_files(str(path), writer, read_gitignore(str(path)), not raw, processed_files, extension)
    
    if not raw:
        writer("</documents>")
    
    output_content = "\n".join(content)
    
    if pbcopy:
        copy_to_clipboard(output_content)
    else:
        click.echo(output_content)

if __name__ == '__main__':
    cli()