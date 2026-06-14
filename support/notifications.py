from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def send_ticket_notification(user_id, data):

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "ticket.notification",
            "data": data
        }
    )
