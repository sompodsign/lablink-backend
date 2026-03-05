#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../../.." && pwd)"

OUT_FILE="$REPO_ROOT/.agents/skills/db/references/thai-learning-schema.md"

cd "$REPO_ROOT"
PYTHONPATH=src DJANGO_SETTINGS_MODULE=core.settings poetry run python - <<'PY' "$OUT_FILE"
from pathlib import Path
import sys
import django
from django.apps import apps

django.setup()
out = Path(sys.argv[1])
out.parent.mkdir(parents=True, exist_ok=True)

models = sorted(apps.get_models(), key=lambda m: (m._meta.app_label, m._meta.model_name))
lines = [
    '# Thai Learning DB Schema Snapshot',
    '',
    'Generated from Django model metadata.',
    '',
    '## Table of Contents',
]
for m in models:
    lines.append(f'- `{m._meta.db_table}` ({m._meta.app_label}.{m.__name__})')

for m in models:
    lines.append('')
    lines.append(f'## `{m._meta.db_table}`')
    lines.append(f'Model: `{m._meta.app_label}.{m.__name__}`')
    lines.append('')
    lines.append('| Column | Type | Null | PK | Unique | Relation |')
    lines.append('|---|---|---|---|---|---|')
    fields = [f for f in m._meta.get_fields() if getattr(f, 'concrete', False)]
    fields.sort(key=lambda f: getattr(f, 'creation_counter', 0))
    for f in fields:
        col = getattr(f, 'column', None) or f.name
        rel = ''
        if getattr(f, 'is_relation', False) and getattr(f, 'related_model', None):
            rel_model = f.related_model
            rel = f'{rel_model._meta.db_table}.{rel_model._meta.pk.column}'
        lines.append(
            f"| `{col}` | `{f.get_internal_type()}` | "
            f"{'yes' if getattr(f, 'null', False) else 'no'} | "
            f"{'yes' if getattr(f, 'primary_key', False) else 'no'} | "
            f"{'yes' if getattr(f, 'unique', False) else 'no'} | `{rel}` |"
        )

out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'Wrote {out}')
PY
