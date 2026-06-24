import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Repoint EventTicket.child, SessionTicket.child, and Ticket.child
    to Attendee (renamed to 'attendee') so that tickets can belong to
    either a Child or a Parent.

    The child_id FK constraints were already dropped in families/0010.
    Here we rename child_id -> attendee_id, add new FK to attendees,
    and update Django state via SeparateDatabaseAndState.
    """

    dependencies = [
        ("events", "0005_add_external_ticket_code"),
        ("families", "0010_convert_child_parent_to_mti"),
    ]

    operations = [
        # ----------------------------------------------------------------
        # EventTicket: child -> attendee
        # ----------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterUniqueTogether(
                    name="eventticket",
                    unique_together=set(),
                ),
                migrations.RemoveIndex(
                    model_name="eventticket",
                    name="event_ticke_child_i_22981b_idx",
                ),
                migrations.RenameField(
                    model_name="eventticket",
                    old_name="child",
                    new_name="attendee",
                ),
                migrations.AlterField(
                    model_name="eventticket",
                    name="attendee",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="event_tickets",
                        to="families.attendee",
                        verbose_name="Attendee",
                    ),
                ),
                migrations.AddIndex(
                    model_name="eventticket",
                    index=models.Index(
                        fields=["attendee"], name="event_ticke_attend_22981b_idx"
                    ),
                ),
                migrations.AlterUniqueTogether(
                    name="eventticket",
                    unique_together={("attendee", "event")},
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    -- Drop old index on child_id
                    DROP INDEX IF EXISTS event_ticke_child_i_22981b_idx;

                    -- Drop unique constraint on (child_id, event_id)
                    ALTER TABLE event_tickets
                        DROP CONSTRAINT IF EXISTS event_tickets_child_id_event_id_b6a9b3a8_uniq;

                    -- Rename child_id -> attendee_id
                    ALTER TABLE event_tickets RENAME COLUMN child_id TO attendee_id;

                    -- Add FK to attendees
                    ALTER TABLE event_tickets
                        ADD CONSTRAINT event_tickets_attendee_id_fk
                        FOREIGN KEY (attendee_id) REFERENCES attendees(id)
                        DEFERRABLE INITIALLY DEFERRED;

                    -- Recreate index on attendee_id
                    CREATE INDEX event_ticke_attend_22981b_idx
                        ON event_tickets (attendee_id);

                    -- Recreate unique constraint on (attendee_id, event_id)
                    ALTER TABLE event_tickets
                        ADD CONSTRAINT event_tickets_attendee_id_event_id_uniq
                        UNIQUE (attendee_id, event_id);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
        # ----------------------------------------------------------------
        # SessionTicket: child -> attendee
        # ----------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterUniqueTogether(
                    name="sessionticket",
                    unique_together=set(),
                ),
                migrations.RemoveIndex(
                    model_name="sessionticket",
                    name="session_tic_child_i_c5a7b7_idx",
                ),
                migrations.RenameField(
                    model_name="sessionticket",
                    old_name="child",
                    new_name="attendee",
                ),
                migrations.AlterField(
                    model_name="sessionticket",
                    name="attendee",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="session_tickets",
                        to="families.attendee",
                        verbose_name="Attendee",
                    ),
                ),
                migrations.AddIndex(
                    model_name="sessionticket",
                    index=models.Index(
                        fields=["attendee"], name="session_tic_attend_c5a7b7_idx"
                    ),
                ),
                migrations.AlterUniqueTogether(
                    name="sessionticket",
                    unique_together={("attendee", "session")},
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    DROP INDEX IF EXISTS session_tic_child_i_c5a7b7_idx;

                    ALTER TABLE session_tickets
                        DROP CONSTRAINT IF EXISTS session_tickets_child_id_session_id_4e835553_uniq;

                    ALTER TABLE session_tickets RENAME COLUMN child_id TO attendee_id;

                    ALTER TABLE session_tickets
                        ADD CONSTRAINT session_tickets_attendee_id_fk
                        FOREIGN KEY (attendee_id) REFERENCES attendees(id)
                        DEFERRABLE INITIALLY DEFERRED;

                    CREATE INDEX session_tic_attend_c5a7b7_idx
                        ON session_tickets (attendee_id);

                    ALTER TABLE session_tickets
                        ADD CONSTRAINT session_tickets_attendee_id_session_id_uniq
                        UNIQUE (attendee_id, session_id);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
        # ----------------------------------------------------------------
        # Ticket (deprecated): child -> attendee
        # ----------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveIndex(
                    model_name="ticket",
                    name="tickets_child_i_0ad1b0_idx",
                ),
                migrations.RenameField(
                    model_name="ticket",
                    old_name="child",
                    new_name="attendee",
                ),
                migrations.AlterField(
                    model_name="ticket",
                    name="attendee",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tickets",
                        to="families.attendee",
                    ),
                ),
                migrations.AddIndex(
                    model_name="ticket",
                    index=models.Index(
                        fields=["attendee"], name="tickets_attend_0ad1b0_idx"
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    DROP INDEX IF EXISTS tickets_child_i_0ad1b0_idx;

                    ALTER TABLE tickets RENAME COLUMN child_id TO attendee_id;

                    ALTER TABLE tickets
                        ADD CONSTRAINT tickets_attendee_id_fk
                        FOREIGN KEY (attendee_id) REFERENCES attendees(id)
                        DEFERRABLE INITIALLY DEFERRED;

                    CREATE INDEX tickets_attend_0ad1b0_idx
                        ON tickets (attendee_id);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
