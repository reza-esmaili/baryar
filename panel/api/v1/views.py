from rest_framework import generics, views, status
from rest_framework.response import Response
from django.db.models import Q
from orders.models import CargoRequest, OrderStatus, OrderHistory
from .permissions import IsForwarderUser
from .serializers import ForwarderOrderListSerializer, ForwarderOrderStatusUpdateSerializer

class ForwarderOrderListAPIView(generics.ListAPIView):
    """لیست سفارشات فورواردر با قابلیت جستجو و فیلتر (مشابه order_list_view)"""
    permission_classes = [IsForwarderUser]
    serializer_class = ForwarderOrderListSerializer

    def get_queryset(self):
        forwarder_company = getattr(self.request.user, 'forwarder_company', None)
        queryset = CargoRequest.objects.filter(
            selected_rate__forwarder=forwarder_company
        ).exclude(status=OrderStatus.DRAFT).select_related(
            'customer__user', 'destination_port'
        ).order_by('-created_at')

        # فیلترها
        q = self.request.query_params.get('q')
        mode = self.request.query_params.get('mode')
        order_status = self.request.query_params.get('status')

        if q:
            queryset = queryset.filter(
                Q(id__icontains=q) | 
                Q(tracking_code__icontains=q) |
                Q(customer__mobile__icontains=q)
            )
        if mode:
            queryset = queryset.filter(transport_mode=mode)
        if order_status:
            queryset = queryset.filter(status=order_status)

        return queryset

class ForwarderOrderStatusUpdateAPIView(views.APIView):
    """تغییر وضعیت یک سفارش به همراه ثبت تاریخچه (مشابه order_detail_view)"""
    permission_classes = [IsForwarderUser]

    def post(self, request, order_id):
        forwarder_company = getattr(request.user, 'forwarder_company', None)
        try:
            order = CargoRequest.objects.get(id=order_id, selected_rate__forwarder=forwarder_company)
        except CargoRequest.DoesNotExist:
            return Response({"detail": "سفارش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ForwarderOrderStatusUpdateSerializer(data=request.data)
        serializer.fields['status'].choices = OrderStatus.choices
        
        if serializer.is_valid():
            new_status = serializer.validated_data['status']
            note = serializer.validated_data.get('note', '')
            old_status = order.status

            if old_status != new_status:
                order.status = new_status
                order.save(update_fields=['status'])
                
                OrderHistory.objects.create(
                    order=order,
                    changed_by=request.user,
                    field_name='status',
                    old_value=old_status,
                    new_value=new_status,
                    note=note
                )
            return Response({"detail": "وضعیت با موفقیت تغییر کرد.", "new_status": new_status})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta

# فرض بر این است که مدل‌های شما با این نام‌ها ایمپورت می‌شوند
from orders.models import CargoRequest
from .permissions import IsForwarderUser

class ForwarderDashboardAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsForwarderUser]

    def get(self, request, *args, **kwargs):
        # پیدا کردن شرکت فورواردری که کاربر به آن متصل است
        forwarder_company = request.user.forwarder_company
        
        # تمام سفارشات ارجاع شده به این فورواردر
        base_queryset = Order.objects.filter(forwarder=forwarder_company)

        # ۱. آمارهای کلی (Summary)
        status_counts = base_queryset.values('status').annotate(count=Count('id'))
        
        # تبدیل خروجی دیتابیس به یک دیکشنری ساده برای فرانت‌اند
        stats = {
            'total_orders': base_queryset.count(),
            'pending_orders': 0,
            'in_progress_orders': 0,
            'completed_orders': 0,
        }
        
        for item in status_counts:
            if item['status'] == 'PENDING':
                stats['pending_orders'] = item['count']
            elif item['status'] == 'IN_PROGRESS':
                stats['in_progress_orders'] = item['count']
            elif item['status'] == 'COMPLETED':
                stats['completed_orders'] = item['count']

        # محاسبه درآمد کل (فرض بر وجود فیلد final_price در سفارشات تکمیل شده)
        total_revenue = base_queryset.filter(status='COMPLETED').aggregate(
            total=Sum('final_price')
        )['total'] or 0

        # ۲. داده‌های نمودار (Chart Data) - مثلا روند ۶ ماه اخیر
        six_months_ago = timezone.now() - timedelta(days=180)
        
        chart_data = base_queryset.filter(created_at__gte=six_months_ago) \
            .annotate(month=TruncMonth('created_at')) \
            .values('month') \
            .annotate(order_count=Count('id')) \
            .order_by('month')

        # فرمت‌دهی داده‌های نمودار برای فلاتر
        formatted_chart_data = [
            {
                "month": entry['month'].strftime('%Y-%m'),
                "order_count": entry['order_count']
            }
            for entry in chart_data
        ]

        return Response({
            "summary": {
                **stats,
                "total_revenue": total_revenue
            },
            "chart_data": formatted_chart_data
        })
