from .models import SupportAgent


def auto_assign_agent(ticket):

    agents = SupportAgent.objects.filter(
        departments=ticket.department
    )

    if agents.exists():
        ticket.assigned_agent = agents.order_by("?").first()
        ticket.save()
