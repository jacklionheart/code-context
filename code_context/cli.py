import os
import subprocess
from pathlib import Path
from typing import List, Set, Optional, Tuple, Callable, Dict
from fnmatch import fnmatch
from dataclasses import dataclass

import click

@dataclass
class Document:
    """Represents a document to be included in the output."""
    index: int
    source: str
    content: str
    is_readme: bool
    depth: int  # Store depth for sorting
    type: Optional[str] = None
    instructions: Optional[str] = None

    @staticmethod
    def from_file(
        file_path: str,
        index: int,
        processed_files: Set[str],
        extensions: Optional[Tuple[str, ...]] = None
    ) -> Optional['Document']:
        """Create a Document from a file if it meets criteria."""
        if file_path in processed_files:
            return None
        if extensions and not any(file_path.endswith(ext) for ext in extensions):
            return None

        try:
            with open(file_path, "r") as f:
                is_readme = file_path.endswith("README.md")
                depth = len(Path(file_path).parts)
                doc = Document(
                    index=index,
                    source=file_path,
                    content=f.read(),
                    is_readme=is_readme,
                    depth=depth
                )
                if is_readme:
                    doc.type = "readme"
                    doc.instructions = doc.content
                processed_files.add(file_path)
                return doc
        except UnicodeDecodeError:
            click.echo(f"Warning: Skipping file {file_path} due to UnicodeDecodeError", err=True)
            return None

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
    """Copy content to clipboard on macOS."""
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
    """Check if path should be ignored according to .gitignore patterns."""
    fname = os.path.basename(path)
    for rule in gitignore_rules:
        if fnmatch(fname, rule):
            return True
        if os.path.isdir(path) and fnmatch(fname + "/", rule):
            return True
    return False

def collect_files(
    path: str,
    gitignore_rules: List[str],
    processed_files: Set[str],
    next_index: int,
    extensions: Optional[Tuple[str, ...]] = None
) -> List[Document]:
    """Recursively collect files into Document objects."""
    documents: List[Document] = []
    current_index = next_index

    def process_file(file_path: str) -> None:
        nonlocal current_index
        doc = Document.from_file(file_path, current_index, processed_files, extensions)
        if doc:
            documents.append(doc)
            current_index += 1

    if os.path.isfile(path):
        process_file(path)
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            # Skip hidden
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files = [f for f in files if not f.startswith(".")]

            # Apply .gitignore
            dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), gitignore_rules)]
            files = [f for f in files if not should_ignore(os.path.join(root, f), gitignore_rules)]

            for file_name in sorted(files):
                process_file(os.path.join(root, file_name))

    return documents

def format_document(doc: Document, raw: bool) -> str:
    """Format a document according to output format."""
    if raw:
        # For raw format, use a strict document structure:
        # 1. Path on a single line
        # 2. Opening separator
        # 3. README markers if needed
        # 4. Content
        # 5. Closing separator
        lines = [
            doc.source,
            "---"
        ]
        if doc.is_readme:
            lines.append("### README START ###")
        lines.append(doc.content)
        if doc.is_readme:
            lines.append("### README END ###")
        lines.append("---")
    else:
        lines = [
            f'<document index="{doc.index}">',
            f"<source>{doc.source}</source>"
        ]
        if doc.type:
            lines.append(f"<type>{doc.type}</type>")
        if doc.instructions:
            lines.extend([
                "<instructions>",
                doc.instructions,
                "</instructions>"
            ])
        else:
            lines.extend([
                "<document_content>",
                doc.content,
                "</document_content>"
            ])
        lines.append("</document>")
    
    return "\n".join(lines)

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
    documents: List[Document] = []
    next_index = 1

    for path_str in paths.split(','):
        path_str = path_str.strip()
        path_obj = resolve_codebase_path(path_str)
        if not path_obj.exists():
            click.echo(f"Warning: Path does not exist: {path_obj}", err=True)
            continue

        # First process READMEs
        readme_docs = []
        for readme_path in find_readmes(path_obj):
            readme_docs.extend(collect_files(
                path=str(readme_path),
                gitignore_rules=[],
                processed_files=processed_files,
                next_index=next_index,
                extensions=extension
            ))
            next_index += len(readme_docs)

        # Then process regular files
        regular_docs = collect_files(
            path=str(path_obj),
            gitignore_rules=read_gitignore(str(path_obj)),
            processed_files=processed_files,
            next_index=next_index,
            extensions=extension
        )
        next_index += len(regular_docs)

        # Add both to our document list
        documents.extend(readme_docs)
        documents.extend(regular_docs)

    # Sort documents ensuring READMEs come first
    documents.sort(key=lambda d: (
        not d.is_readme,  # False sorts before True, so READMEs come first
        d.depth,         # Then by directory depth
        d.source        # Then by path alphabetically
    ))

    # Re-index documents to ensure sequential numbering
    for i, doc in enumerate(documents, 1):
        doc.index = i

    # Generate output
    output_lines = []
    if not raw:
        output_lines.append("<documents>")
    
    for doc in documents:
        output_lines.append(format_document(doc, raw))
    
    if not raw:
        output_lines.append("</documents>")

    output_content = "\n".join(output_lines)

    if pbcopy:
        copy_to_clipboard(output_content)
    else:
        click.echo(output_content)

if __name__ == "__main__":
    cli()