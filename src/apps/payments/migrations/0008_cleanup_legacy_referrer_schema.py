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


def cleanup_legacy_referrer_schema(apps, schema_editor):
    cursor = schema_editor.connection.cursor()

    if not _table_exists(cursor, "apps_referrer"):
        return

    if _column_exists(cursor, "apps_referrer", "specialty"):
        cursor.execute("ALTER TABLE apps_referrer DROP COLUMN specialty")

    if _column_exists(cursor, "apps_referrer", "phone"):
        cursor.execute(
            """
            UPDATE apps_referrer
            SET phone = ''
            WHERE phone IS NULL
            """
        )
        cursor.execute(
            """
            ALTER TABLE apps_referrer
            ALTER COLUMN phone SET DEFAULT '',
            ALTER COLUMN phone SET NOT NULL
            """
        )

    if _column_exists(cursor, "apps_referrer", "type"):
        cursor.execute(
            """
            UPDATE apps_referrer
            SET type = 'DOCTOR'
            WHERE type IS NULL OR type = ''
            """
        )
        cursor.execute(
            """
            ALTER TABLE apps_referrer
            ALTER COLUMN type SET DEFAULT 'DOCTOR',
            ALTER COLUMN type SET NOT NULL
            """
        )

    if _column_exists(cursor, "apps_referrer", "notes"):
        cursor.execute(
            """
            UPDATE apps_referrer
            SET notes = ''
            WHERE notes IS NULL
            """
        )
        cursor.execute(
            """
            ALTER TABLE apps_referrer
            ALTER COLUMN notes SET DEFAULT '',
            ALTER COLUMN notes SET NOT NULL
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0007_upgrade_existing_referral_schema"),
    ]

    operations = [
        migrations.RunPython(
            cleanup_legacy_referrer_schema,
            migrations.RunPython.noop,
        ),
    ]
