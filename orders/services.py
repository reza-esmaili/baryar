from decimal import Decimal
from django.utils import timezone
from rates.models import RateTier

def calculate_and_match_rates(data, dimensions_data):
    transport_mode = data.get('transport_mode')
    is_fcl = transport_mode in ['sea_fcl', 'FCL']
    
    # 1. محاسبه وزن حجمی
    total_volumetric_weight = Decimal('0.0')
    if not is_fcl and dimensions_data:
        divisor = Decimal('6000') # برای حمل هوایی
        for dim in dimensions_data:
            if dim and not dim.get('DELETE', False) and dim.get('length'):
                volume = dim['length'] * dim['width'] * dim['height'] * dim['quantity']
                total_volumetric_weight += Decimal(str(volume)) / divisor
            
    # 2. تعیین Chargeable Weight
    # بررسی همزمان کلیدهای فلاتر (gross_weight) و جنگو (actual_weight)
    weight_val = data.get('gross_weight') or data.get('actual_weight') or '0.0'
    actual_wt = Decimal(str(weight_val))
    cw = max(actual_wt, total_volumetric_weight)

    # 3. ساخت فیلترهای پایه برای جستجوی نرخ‌ها به صورت داینامیک
    query_filters = {
        'rate__is_active': True,
        'rate__valid_until__gte': timezone.now().date(),
        'rate__transport_mode': transport_mode,
    }

    # فیلتر مبدا (شناسایی اینکه دیتا از فلاتر آمده یا جنگو)
    if data.get('origin_id'):
        query_filters['rate__origin_city_id'] = data.get('origin_id')
    elif data.get('origin_city'):
        query_filters['rate__origin_city'] = data.get('origin_city')

    # فیلتر مقصد
    if data.get('destination_id'):
        query_filters['rate__destination_port_id'] = data.get('destination_id')
    elif data.get('destination_port'):
        query_filters['rate__destination_port'] = data.get('destination_port')

    # فیلتر نوع بار (فقط اگر از فرانت ارسال شده باشد اعمال می‌شود)
    if data.get('cargo_type'):
        query_filters['rate__cargo_types'] = data.get('cargo_type')

    # اعمال فیلترها روی دیتابیس
    base_query = RateTier.objects.filter(**query_filters).select_related(
        'rate', 'rate__forwarder', 'rate__branch', 'rate__branch__company'
    )

    if is_fcl:
        fcl_filters = {'container_size': data.get('container_size')}
        # فقط در صورتی که container_type ارسال شده باشد فیلتر می‌کنیم
        if data.get('container_type'):
            fcl_filters['container_type'] = data.get('container_type')
        
        valid_tiers = base_query.filter(**fcl_filters)
    else:
        valid_tiers = base_query.filter(
            weight_from__lte=cw,
            weight_to__gte=cw
        )

    results = []
    for tier in valid_tiers:
        if is_fcl:
            count = data.get('container_count') or 1
            price = tier.price * int(count) # اطمینان از عدد بودن کانتیت
        else:
            price = tier.price * cw if tier.pricing_unit == 'per_kg' else tier.price
            
        rate = tier.rate
        if rate.forwarder:
            company_name = rate.forwarder.company_name
        elif hasattr(rate, 'branch') and rate.branch:
            company_name = rate.branch.company.company_name
        else:
            company_name = "ناشناس"

        results.append({
            'rate_id': rate.id,
            'company_name': company_name,
            'unit_price': str(tier.price),
            'total_price': str(price),
        })
    print("=== DEBUG FILTERS ===")
    print("Query Filters:", query_filters)
    print("Chargeable Weight (cw):", cw)
    print("Found Tiers Count:", valid_tiers.count())

    results = sorted(results, key=lambda x: Decimal(x['total_price']))
    
    return {
        'actual_weight': str(actual_wt),             
        'volumetric_weight': str(total_volumetric_weight),
        'chargeable_weight': str(cw),
        'results': results
    }
