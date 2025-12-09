<script lang="ts">
  type TicketType = 'event' | 'session' | 'none';

  interface Props {
    type: TicketType;
  }

  let { type }: Props = $props();

  const styles = {
    event: 'bg-success-600',
    session: 'bg-primary-600',
    none: 'bg-danger-600'
  };

  const labels = {
    event: 'Event Pass',
    session: 'Session Ticket',
    none: 'No Ticket'
  };
</script>

<div class="flex items-center gap-2">
  <span class="w-3 h-3 rounded-full {styles[type]}"></span>
  <span class="text-sm">{labels[type]}</span>
</div>
