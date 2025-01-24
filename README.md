# code-context

A tool for providing intelligent codebase context to Large Language Models (LLMs).

Built on [files-to-prompt](https://github.com/simonw/files-to-prompt).

## Features

### README Highlighting
READMEs are pulled out into a separate section of the output at the top of the context.

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

## Installation

from root:
```bash
pip install -e .
```

## Usage

Copy `manabot` codebase to clipboard (OS X only):
```bash
code-context -p manabot
```

Copy multiple codebases and directories:
```bash
code-context manabot,managym/agent,managym/tests
```

Filter to python and use raw (non-XML) output
```bash
code-context -e .py -r manabot 
```

## Directory Structure Assumptions

- Projects live in $CODE_CONTEXT_ROOT (default: ~/src)
- Automatically traverse repeated directory names (e.g. `manabot/manabot/env` -> `manabot/env`)
- READMEs at any level are automatically included
