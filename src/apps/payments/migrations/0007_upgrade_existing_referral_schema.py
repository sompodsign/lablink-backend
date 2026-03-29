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


def upgrade_existing_referral_schema(apps, schema_editor):
    cursor = schema_editor.connection.cursor()

    if _table_exists(cursor, "apps_referral_doctor") and not _table_exists(
        cursor, "apps_referrer"
    ):
        cursor.execute("ALTER TABLE apps_referral_doctor RENAME TO apps_referrer")

    if _table_exists(cursor, "apps_referrer"):
        if not _column_exists(cursor, "apps_referrer", "type"):
            cursor.execute(
                """
                ALTER TABLE apps_referrer
                ADD COLUMN type varchar(20) NOT NULL DEFAULT 'DOCTOR'
                """
            )
        if not _column_exists(cursor, "apps_referrer", "notes"):
            cursor.execute(
                """
                ALTER TABLE apps_referrer
                ADD COLUMN notes text NOT NULL DEFAULT ''
                """
            )

    if _column_exists(
        cursor, "apps_billing_invoice", "referral_doctor_id"
    ) and not _column_exists(cursor, "apps_billing_invoice", "referrer_id"):
        cursor.execute(
            """
            ALTER TABLE apps_billing_invoice
            RENAME COLUMN referral_doctor_id TO referrer_id
            """
        )

    if not _column_exists(cursor, "apps_billing_invoice", "referrer_name_snapshot"):
        cursor.execute(
            """
            ALTER TABLE apps_billing_invoice
            ADD COLUMN referrer_name_snapshot varchar(200) NOT NULL DEFAULT ''
            """
        )

    if not _column_exists(cursor, "apps_billing_invoice", "commission_pct_snapshot"):
        cursor.execute(
            """
            ALTER TABLE apps_billing_invoice
            ADD COLUMN commission_pct_snapshot numeric(5, 2) NOT NULL DEFAULT 0.00
            """
        )

    if not _column_exists(cursor, "apps_billing_invoice", "paid_at"):
        cursor.execute(
            """
            ALTER TABLE apps_billing_invoice
            ADD COLUMN paid_at timestamp with time zone NULL
            """
        )

    if _table_exists(cursor, "apps_referrer"):
        cursor.execute(
            """
            UPDATE apps_billing_invoice AS invoice
            SET
                referrer_name_snapshot = COALESCE(referrer.name, ''),
                commission_pct_snapshot = COALESCE(referrer.commission_pct, 0.00),
                paid_at = CASE
                    WHEN invoice.status = 'PAID' AND invoice.paid_at IS NULL
                    THEN invoice.created_at
                    ELSE invoice.paid_at
                END
            FROM apps_referrer AS referrer
            WHERE invoice.referrer_id = referrer.id
              AND (
                  invoice.referrer_name_snapshot = ''
                  OR invoice.commission_pct_snapshot = 0.00
                  OR (invoice.status = 'PAID' AND invoice.paid_at IS NULL)
              )
            """
        )
        cursor.execute(
            """
            UPDATE apps_billing_invoice
            SET paid_at = created_at
            WHERE status = 'PAID'
              AND paid_at IS NULL
            """
        )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS apps_referrer_settlement (
            id bigserial PRIMARY KEY,
            settlement_number varchar(50) UNIQUE NOT NULL,
            amount_paid numeric(10, 2) NOT NULL,
            payment_method varchar(20) NOT NULL DEFAULT 'CASH',
            notes text NOT NULL DEFAULT '',
            paid_at timestamp with time zone NOT NULL,
            created_at timestamp with time zone NOT NULL DEFAULT NOW(),
            center_id bigint NOT NULL
                REFERENCES core_diagnostic_center(id)
                DEFERRABLE INITIALLY DEFERRED,
            created_by_id bigint NULL
                REFERENCES users_user(id)
                DEFERRABLE INITIALLY DEFERRED,
            referrer_id bigint NOT NULL
                REFERENCES apps_referrer(id)
                DEFERRABLE INITIALLY DEFERRED
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS apps_referrer_settlement_item (
            id bigserial PRIMARY KEY,
            allocated_amount numeric(10, 2) NOT NULL,
            created_at timestamp with time zone NOT NULL DEFAULT NOW(),
            invoice_id bigint NOT NULL
                REFERENCES apps_billing_invoice(id)
                DEFERRABLE INITIALLY DEFERRED,
            settlement_id bigint NOT NULL
                REFERENCES apps_referrer_settlement(id)
                DEFERRABLE INITIALLY DEFERRED
        )
        """
    )

    cursor.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'unique_settlement_invoice_allocation'
            ) THEN
                ALTER TABLE apps_referrer_settlement_item
                ADD CONSTRAINT unique_settlement_invoice_allocation
                UNIQUE (settlement_id, invoice_id);
            END IF;
        END$$;
        """
    )

    cursor.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'referrer_allocated_amount_gt_zero'
            ) THEN
                ALTER TABLE apps_referrer_settlement_item
                ADD CONSTRAINT referrer_allocated_amount_gt_zero
                CHECK (allocated_amount > 0.00);
            END IF;
        END$$;
        """
    )


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0006_add_referral_commission"),
    ]

    operations = [
        migrations.RunPython(
            upgrade_existing_referral_schema,
            migrations.RunPython.noop,
        ),
    ]
