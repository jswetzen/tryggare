import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Repoint CheckInRecord.child to Attendee (renamed to 'attendee').

    The child_id FK constraint was already dropped in families/0010.
    Here we rename child_id -> attendee_id, add new FK to attendees,
    and update Django state via SeparateDatabaseAndState.
    """

    dependencies = [
        ("checkins", "0005_auditlog_user_nullable"),
        ("families", "0010_convert_child_parent_to_mti"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                # Drop the unique constraint that references 'child'
                migrations.RemoveConstraint(
                    model_name="checkinrecord",
                    name="unique_check_in_per_session",
                ),
                # Drop the index on 'child'
                migrations.RemoveIndex(
                    model_name="checkinrecord",
                    name="check_in_re_child_i_5f734e_idx",
                ),
                # Rename field in state
                migrations.RenameField(
                    model_name="checkinrecord",
                    old_name="child",
                    new_name="attendee",
                ),
                # Alter field to point at Attendee
                migrations.AlterField(
                    model_name="checkinrecord",
                    name="attendee",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="checkin_records",
                        to="families.attendee",
                        verbose_name="Attendee",
                    ),
                ),
                # Re-add index on 'attendee'
                migrations.AddIndex(
                    model_name="checkinrecord",
                    index=models.Index(
                        fields=["attendee"], name="check_in_re_attend_5f734e_idx"
                    ),
                ),
                # Recreate the unique constraint
                migrations.AddConstraint(
                    model_name="checkinrecord",
                    constraint=models.UniqueConstraint(
                        fields=["attendee", "session", "check_in_time"],
                        name="unique_check_in_per_session",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    -- Drop old index on child_id
                    DROP INDEX IF EXISTS check_in_re_child_i_5f734e_idx;

                    -- Drop unique constraint referencing child_id
                    ALTER TABLE check_in_records
                        DROP CONSTRAINT IF EXISTS unique_check_in_per_session;

                    -- Rename child_id -> attendee_id
                    ALTER TABLE check_in_records RENAME COLUMN child_id TO attendee_id;

                    -- Add FK to attendees
                    ALTER TABLE check_in_records
                        ADD CONSTRAINT check_in_records_attendee_id_fk
                        FOREIGN KEY (attendee_id) REFERENCES attendees(id)
                        DEFERRABLE INITIALLY DEFERRED;

                    -- Recreate index on attendee_id
                    CREATE INDEX check_in_re_attend_5f734e_idx
                        ON check_in_records (attendee_id);

                    -- Recreate unique constraint on (attendee_id, session_id, check_in_time)
                    ALTER TABLE check_in_records
                        ADD CONSTRAINT unique_check_in_per_session
                        UNIQUE (attendee_id, session_id, check_in_time);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
