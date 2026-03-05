---
globs: "**/*.py"
---

# Python Code Style

- Line length: 120 characters max
- Single quotes for strings (not double quotes)
- Indent: 4 spaces
- Python 3.12+ — use modern syntax (type unions `X | Y`, `match/case`, etc.)
- No `print()` statements — use `logger` instead (ruff T201 enforced)
- No `from module import *` except in settings files
- Max cyclomatic complexity: 12
- Prefix unused variables with underscore (`_unused`)

## Import Ordering (ruff isort)

Order: stdlib → django → third-party → local (`src/`, `libs/`) → relative (`.`)

```python
# 1. Standard library
import json
from datetime import datetime
from decimal import Decimal

# 2. Django
from django.conf import settings
from django.db import models

# 3. Third-party
from pydantic import BaseModel
from rest_framework import serializers

# 4. Local absolute
from src.core.account.models import Account
from src.utils.logger import get_logger

# 5. Relative
from .schema import SCHEMA
```

- Case-sensitive sorting
- Combine as-imports: `from x import (A as A1, B as B1)`
- Force wrap aliases on long lines
