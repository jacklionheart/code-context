# code-context

A tool for providing intelligent codebase context to Large Language Models (LLMs).

Built on [files-to-prompt](https://github.com/simonw/files-to-prompt).

## Features

### Hierarchical README inclusion
If there is a README in a containing directory for any paths provided, it will be included.
For example, if you provide `codebase/env/data`, `codebase/env/README.md` will be included.

### Intelligent Path Resolution
- All paths are relative to $CODE_CONTEXT_ROOT (default: ~/src)
- The first directory in any path is considered the codebase name
- We handle cases where codebase names are repeated:
    - Direct access: `codebase/env` -> `$CODE_CONTEXT_ROOT/codebase/env`
    - Auto-prefixed: `codebase/env` -> `$CODE_CONTEXT_ROOT/codebase/codebase/env` (if direct path doesn't exist)
- Special cases:
    - Tests directory is always at `codebase/tests`
    - Root files (like README.md) are accessed directly

### File filtering
Filter included files by extension:
```bash
code-context -e .py -e .js manabot  # only Python and JS files
```

## Installation

from root:
```bash
pip install -e .
```

## Usage

Copy `manabot` codebase to clipboard:
```bash
code-context -c manabot
```

Copy multiple codebases and directories:
```bash
code-context manabot,managym/agent,managym/tests
```

Specify generate output stream instead of pbcopy:
```bash
code-context -o manabot/env > context.txt
```

## Directory Structure Assumptions

- Projects live in $CODE_CONTEXT_ROOT (default: ~/src)
- Automatically traverse repeated directory names (e.g. `manabot/manabot/env` -> `manabot/env`)
- READMEs at any level are automatically included
