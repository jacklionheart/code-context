# code-context

A tool for providing intelligent codebase context to Large Language Models (LLMs).

Built on [files-to-prompt](https://github.com/simonw/files-to-prompt). 

## Features

### Hierarchical README inclusion
If there is a README in a containing directory for any paths provided, it will be included.
For example, if you provide `codebase/env/data`, `codebase/env/README.md` will be included.

### Leverage codebase layout assumptions to shorten commands
- All paths provided are relative to $CODE_CONTEXT_ROOT (default: ~/src)
- The first directory in any path is considered the codebase name.
- We assume that:
    - Tests are located in `codebase/tests`
    - All other subdirectories will be auto-prefixed with `codebase/` For example, `codebase/env/data` will actually search `$CODE_CONTEXT_ROOT/codebase/codebase/env/data`


code-context defaults to Claude XML format, but you can use raw format with `-r`.

### File filtering

## Installation

from root:
```bash
pip install -e .
```

## Usage

Copy `manabot` codebase to OS X clipboard:
```bash
code-context -p manabot
```

Output to a file, using raw format:
```bash
code-context -r manabot/env > context.txt
```

Filter included files by extension:
```bash
code-context -e .py -e .js manabot  # only Python and JS files
```

Copy multiple codebases and directories:
```bash
code-context manabot,managym/agent,managym/tests
```



## Directory Structure Assumptions

- Projects live in $CODE_CONTEXT_ROOT (default: ~/src)
- Automatically traverse repeated directory names (e.g. `manabot/manabot/env` -> `manabot/env`)
- READMEs at any level are automatically included
