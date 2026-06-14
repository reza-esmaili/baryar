from django.utils import timezone
from .models import Ticket, SLA


def check_sla():

    tickets = Ticket.objects.filter(
        status="open"
    )

    for ticket in tickets:

        sla = SLA.objects.filter(
            department=ticket.department
        ).first()

        if not sla:
            continue

        deadline = ticket.created_at + timezone.timedelta(
            minutes=sla.response_time
        )

        if timezone.now() > deadline:
            ticket.priority = "urgent"
            ticket.save()
