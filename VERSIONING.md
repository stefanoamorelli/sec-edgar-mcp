# Versioning Strategy

## Overview
This project uses semantic versioning (semver) with a single source of truth for the version number.

## Version Sources

### 1. PyPI / Python Package (`pyproject.toml`)
- **Location**: `pyproject.toml` → `[project]` → `version`
- **Current**: `1.1.0`
- **Usage**: This is the PRIMARY version source
- **When to update**: Before creating a release tag

### 2. Python Module (`sec_edgar_mcp/__init__.py`)
- **Location**: `sec_edgar_mcp/__init__.py` → `__version__`
- **Current**: `1.1.0`
- **Usage**: Runtime version identification
- **Must match**: `pyproject.toml` version

### 3. Lockfile (`uv.lock`)
- **Location**: `uv.lock` → the `sec-edgar-mcp` package entry
- **Usage**: Re-run `uv lock` after changing the version so the lockfile matches
- **Must match**: `pyproject.toml` version

## Release Process

### 1. Update Version Numbers
Before creating a release:
```bash
# Update pyproject.toml
version = "1.0.0"  # Remove -alpha, use proper semver

# Update sec_edgar_mcp/__init__.py
__version__ = "1.0.0"  # Must match pyproject.toml
```

### 2. Create Git Tag
```bash
git add -A
git commit -m "chore: bump version to 1.0.0"
git tag v1.0.0
git push origin main --tags
```

### 3. Create GitHub Release
1. Go to GitHub Releases
2. Create release from tag `v1.0.0`
3. This triggers:
   - PyPI publishing (uses `pyproject.toml` version)
   - Docker publishing (uses Git tag)

## Version Format

### Development Versions
- Format: `X.Y.Z-alpha` or `X.Y.Z-beta`
- Example: `1.0.0-alpha`

### Release Versions
- Format: `X.Y.Z`
- Example: `1.0.0`, `1.0.1`, `1.1.0`

### Pre-releases
- Format: `X.Y.Z-rc.N`
- Example: `1.0.0-rc.1`, `1.0.0-rc.2`

## Important Notes

1. **Git tags must start with 'v'**: `v1.0.0`, not `1.0.0`
2. **PyPI version must match exactly**: What's in `pyproject.toml` is what gets published
3. **Always update all three**: `pyproject.toml`, `__init__.py`, and `uv.lock`

## Checking Current Version

```bash
# Check package version
python -c "import sec_edgar_mcp; print(sec_edgar_mcp.__version__)"

# Check git tags
git describe --tags --abbrev=0

# Check pyproject.toml
grep "^version" pyproject.toml
```