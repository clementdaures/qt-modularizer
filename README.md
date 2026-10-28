# qt-modularizer

Companion tool for Qt Designer: load a `.ui` file, assign semantic roles, tune the Daeria design system palettes and
export a modular `src/ui/` package with theme support.

Requires Python 3.11+.

## Development

```
pip install -e .[dev]
pytest
```

`daeria-log` is vendored in `external/daeria-log` and picked up automatically when it is not installed.