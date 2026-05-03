# ADR 002: Pydantic v1/v2 Compatibility Strategy

## Status
Accepted

## Context
SRT2Web needs to support both Pydantic v1 and v2 due to various dependencies. Some packages (like whisper) may require Pydantic v1, while newer packages use v2. The `config_manager.py` was failing with `ImportError: cannot import name 'ValidationError' from 'pydantic_core'`.

Key issues:
- Pydantic v2 uses `pydantic_core` for core functionality
- Pydantic v1 uses `pydantic.errors` for `ValidationError`
- Import statements need to handle both versions gracefully
- The codebase should work with either version

## Decision
We decided to implement a try-except import strategy for Pydantic imports:

```python
try:
    from pydantic import BaseModel, ValidationError
    USING_PYDANTIC_V2 = True
except ImportError:
    from pydantic.v1 import BaseModel
    from pydantic.errors import ValidationError
    USING_PYDANTIC_V2 = False
```

This approach:
1. **Tries Pydantic v2 first** (preferred for new code)
2. **Falls back to v1** if v2 imports fail
3. **Sets a flag** to track which version is being used
4. **Minimizes code changes** - only affects import statements

## Consequences

### Positive
- **Backward compatibility**: Works with both Pydantic v1 and v2
- **Minimal changes**: Only import statements need modification
- **Clear intent**: The try-except pattern is explicit about compatibility
- **Future-proof**: Can migrate fully to v2 when all dependencies support it

### Negative
- **Extra complexity**: Import blocks are slightly more verbose
- **Testing burden**: Need to test with both Pydantic versions
- **Potential confusion**: Developers might not know which version is being used

### Mitigations
- Document the compatibility strategy in `docs/compatibility.md`
- Add logging to indicate which Pydantic version is loaded
- Gradually migrate to v2-only when dependencies are updated
- Add CI tests with both Pydantic versions

## References
- `core/config_manager.py` - Uses try-except import strategy
- `docs/compatibility.md` - Documents Pydantic version compatibility
- Pydantic v2 migration guide: https://docs.pydantic.dev/latest/migration/

## Date
2026-05-03
