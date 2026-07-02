import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Convert Child and Parent to MTI subclasses of Attendee.

    State side: Delete old models, recreate them as MTI subclasses of Attendee.
    DB side: raw SQL to:
      1. Drop FK constraints from dependent tables (tickets, event_tickets,
         session_tickets, check_in_records) that reference children.id / parents.id
         — these will be recreated in events/0006 and checkins/0006.
      2. Rename id -> attendee_ptr_id on children and parents, add FK to attendees,
         drop duplicated columns.

    This migration is NOT reversible.
    """

    dependencies = [
        ("families", "0010_backfill_attendees"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # ----------------------------------------------------------------
            # STATE SIDE — recreate Child and Parent as MTI subclasses
            # ----------------------------------------------------------------
            state_operations=[
                # --- Child: delete old model state, recreate as MTI subclass ---
                migrations.DeleteModel(name="Child"),
                migrations.CreateModel(
                    name="Child",
                    fields=[
                        (
                            "attendee_ptr",
                            models.OneToOneField(
                                auto_created=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                parent_link=True,
                                primary_key=True,
                                serialize=False,
                                to="families.attendee",
                            ),
                        ),
                        (
                            "birthdate",
                            models.DateField(
                                blank=True, null=True, verbose_name="Birthdate"
                            ),
                        ),
                        (
                            "allergies",
                            models.TextField(
                                blank=True, null=True, verbose_name="Allergies"
                            ),
                        ),
                        (
                            "notes",
                            models.TextField(
                                blank=True, null=True, verbose_name="Notes"
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Child",
                        "verbose_name_plural": "Children",
                        "db_table": "children",
                    },
                    bases=("families.attendee",),
                ),
                # --- Parent: delete old model state, recreate as MTI subclass ---
                migrations.DeleteModel(name="Parent"),
                migrations.CreateModel(
                    name="Parent",
                    fields=[
                        (
                            "attendee_ptr",
                            models.OneToOneField(
                                auto_created=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                parent_link=True,
                                primary_key=True,
                                serialize=False,
                                to="families.attendee",
                            ),
                        ),
                        (
                            "phone",
                            models.CharField(
                                blank=True,
                                max_length=50,
                                null=True,
                                verbose_name="Phone",
                            ),
                        ),
                        (
                            "phone_locked",
                            models.BooleanField(
                                default=False,
                                help_text="When checked, re-imports will not overwrite this phone number.",
                                verbose_name="Phone Locked",
                            ),
                        ),
                        (
                            "email",
                            models.EmailField(
                                blank=True, null=True, verbose_name="Email"
                            ),
                        ),
                        (
                            "email_locked",
                            models.BooleanField(
                                default=False,
                                help_text="When checked, re-imports will not overwrite this email address.",
                                verbose_name="Email Locked",
                            ),
                        ),
                        (
                            "relationship_type",
                            models.CharField(
                                max_length=64, verbose_name="Relationship Type"
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Parent",
                        "verbose_name_plural": "Parents",
                        "db_table": "parents",
                    },
                    bases=("families.attendee",),
                ),
            ],
            # ----------------------------------------------------------------
            # DATABASE SIDE — raw SQL to transform the tables
            # ----------------------------------------------------------------
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    -- =========================================================
                    -- Step 1: Drop FK constraints from dependent tables that
                    -- reference children.id (so we can modify children's PK).
                    -- These FKs will be recreated in events/0006 and checkins/0006.
                    -- =========================================================
                    ALTER TABLE tickets DROP CONSTRAINT IF EXISTS tickets_child_id_e1ab1e9e_fk_children_id;
                    ALTER TABLE event_tickets DROP CONSTRAINT IF EXISTS event_tickets_child_id_c6737e06_fk_children_id;
                    ALTER TABLE session_tickets DROP CONSTRAINT IF EXISTS session_tickets_child_id_d484de04_fk_children_id;
                    ALTER TABLE check_in_records DROP CONSTRAINT IF EXISTS check_in_records_child_id_f5586a66_fk_children_id;

                    -- =========================================================
                    -- Step 2: CHILDREN table — convert id -> attendee_ptr_id
                    -- =========================================================

                    -- Drop indexes referencing old columns
                    DROP INDEX IF EXISTS children_last_na_7c9895_idx;
                    DROP INDEX IF EXISTS children_family__fb1a34_idx;

                    -- Add attendee_ptr_id as a plain UUID column, copy id, make PK
                    ALTER TABLE children ADD COLUMN attendee_ptr_id uuid;
                    UPDATE children SET attendee_ptr_id = id;
                    ALTER TABLE children ALTER COLUMN attendee_ptr_id SET NOT NULL;

                    -- Add FK constraint to attendees
                    ALTER TABLE children
                        ADD CONSTRAINT children_attendee_ptr_id_fk
                        FOREIGN KEY (attendee_ptr_id) REFERENCES attendees(id)
                        DEFERRABLE INITIALLY DEFERRED;

                    -- Drop old PK (no dependents remain) and old id column
                    ALTER TABLE children DROP CONSTRAINT children_pkey;
                    ALTER TABLE children DROP COLUMN id;

                    -- Make attendee_ptr_id the new PK
                    ALTER TABLE children ADD PRIMARY KEY (attendee_ptr_id);

                    -- Drop columns that moved to attendees
                    ALTER TABLE children DROP COLUMN first_name;
                    ALTER TABLE children DROP COLUMN last_name;
                    ALTER TABLE children DROP COLUMN last_participation_date;
                    ALTER TABLE children DROP COLUMN family_id;

                    -- =========================================================
                    -- Step 3: PARENTS table — same pattern
                    -- =========================================================

                    DROP INDEX IF EXISTS parents_family__12cac8_idx;

                    ALTER TABLE parents ADD COLUMN attendee_ptr_id uuid;
                    UPDATE parents SET attendee_ptr_id = id;
                    ALTER TABLE parents ALTER COLUMN attendee_ptr_id SET NOT NULL;

                    ALTER TABLE parents
                        ADD CONSTRAINT parents_attendee_ptr_id_fk
                        FOREIGN KEY (attendee_ptr_id) REFERENCES attendees(id)
                        DEFERRABLE INITIALLY DEFERRED;

                    ALTER TABLE parents DROP CONSTRAINT parents_pkey;
                    ALTER TABLE parents DROP COLUMN id;
                    ALTER TABLE parents ADD PRIMARY KEY (attendee_ptr_id);

                    -- Drop columns that moved to attendees (+ old name column)
                    ALTER TABLE parents DROP COLUMN name;
                    ALTER TABLE parents DROP COLUMN last_participation_date;
                    ALTER TABLE parents DROP COLUMN family_id;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
