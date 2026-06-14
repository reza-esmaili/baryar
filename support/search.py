# support/search.py
from .models import Ticket

def filter_tickets(queryset, params):
    """
    params می تواند شامل وضعیت، اولویت یا دپارتمان باشد
    """
    if params.get('status'):
        queryset = queryset.filter(status=params.get('status'))
    
    if params.get('priority'):
        queryset = queryset.filter(priority=params.get('priority'))
        
    if params.get('q'):
        query = params.get('q')
        queryset = queryset.filter(subject__icontains=query)
        
    return queryset
