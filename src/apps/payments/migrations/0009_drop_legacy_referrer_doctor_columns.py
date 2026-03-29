from django.db import migrations


def _table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = current_schema()
              AND table_name = %s
        )
        """,
        [table_name],
    )
    return cursor.fetchone()[0]


def _column_exists(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = %s
              AND column_name = %s
        )
        """,
        [table_name, column_name],
    )
    return cursor.fetchone()[0]


def drop_legacy_referrer_doctor_columns(apps, schema_editor):
    cursor = schema_editor.connection.cursor()

    if not _table_exists(cursor, "apps_referrer"):
        return

    for column_name in ("specialty", "specialization"):
        if _column_exists(cursor, "apps_referrer", column_name):
            cursor.execute(f"ALTER TABLE apps_referrer DROP COLUMN {column_name}")


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0008_cleanup_legacy_referrer_schema"),
    ]

    operations = [
        migrations.RunPython(
            drop_legacy_referrer_doctor_columns,
            migrations.RunPython.noop,
        ),
    ]
