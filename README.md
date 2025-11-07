# toggl-round
Round time entries entered into Toggl to the nearest quarter hour.

The Toggl iOS application automatically includes the seconds with each start and stop time. 
When entering time into separate systems in which you need to round your time to
the nearest quarter hour, this creates uneven portions of time (i.e. 1.26 or 3.51 hours).

This command will first truncate all of the second parts of the datetime stamp of each entry,
then will round each to the nearest quarter hour.

## Development setup (uv)
This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

Install uv (if not already):
```
pip install uv
```

Install runtime dependencies:
```
uv sync
```

Install with development dependencies (tests, linting, tooling):
```
uv sync --group dev
```

Add a runtime dependency:
```
uv add <package>
```

Add a development dependency:
```
uv add --group dev <package>
```

Update the lock file after changes:
```
uv lock
```

Run the script:
```
uv run python time_entry_rounding.py
```

Spawn an interactive shell with all dependencies:
```
uv run ipython
```

## Notes
Runtime vs development dependencies are separated in `pyproject.toml` using `optional-dependencies.dev`.
Type stubs and editor/lint tooling live in the `dev` group.
