from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from rates.models import RateTier, ExtraChargeType


VAT_RATE = Decimal("0.10")


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_extra_charge(charge_type, unit_price, weight):
    unit_price = Decimal(str(unit_price or 0))
    weight = Decimal(str(weight or 0))

    if charge_type == ExtraChargeType.NOT_AVAILABLE:
        return Decimal("0.00")

    if charge_type == ExtraChargeType.FREE:
        return Decimal("0.00")

    if charge_type == ExtraChargeType.FIXED:
        return unit_price

    if charge_type == ExtraChargeType.PER_KG:
        return unit_price * weight

    return Decimal("0.00")


def calculate_and_match_rates(data, dimensions_data):
    transport_mode = data.get('transport_mode')
    shipping_procedure = data.get('shipping_procedure')
    is_fcl = transport_mode in ['sea_fcl', 'FCL']
    needs_packaging = bool(data.get('needs_packaging'))
    needs_doorstep_packaging = bool(data.get('needs_doorstep_packaging'))

    # 1. محاسبه وزن حجمی
    total_volumetric_weight = Decimal('0.0')

    if not is_fcl and dimensions_data:
        divisor = Decimal('6000')

        for dim in dimensions_data:
            if dim and not dim.get('DELETE', False) and dim.get('length'):
                volume = (
                    Decimal(str(dim['length'])) *
                    Decimal(str(dim['width'])) *
                    Decimal(str(dim['height'])) *
                    Decimal(str(dim['quantity']))
                )
                total_volumetric_weight += volume / divisor

    # 2. تعیین Chargeable Weight
    weight_val = data.get('gross_weight') or data.get('actual_weight') or '0.0'
    actual_wt = Decimal(str(weight_val))
    cw = max(actual_wt, total_volumetric_weight)

    # 3. ساخت فیلترهای پایه برای جستجوی نرخ‌ها
    query_filters = {
        'rate__is_active': True,
        'rate__valid_until__gte': timezone.now().date(),
        'rate__transport_mode': transport_mode,
    }

    if shipping_procedure:
        query_filters['rate__shipping_procedure'] = shipping_procedure

    # کشور مبدا
    if data.get('origin_country'):
        query_filters['rate__origin_country_id'] = data.get('origin_country')

    # استان مبدا
    if data.get('origin_province'):
        query_filters['rate__origin_province_id'] = data.get('origin_province')

    # شهر مبدا
    if data.get('origin_id'):
        query_filters['rate__origin_city_id'] = data.get('origin_id')
    elif data.get('origin_city'):
        query_filters['rate__origin_city'] = data.get('origin_city')

    # مقصد
    if data.get('destination_id'):
        query_filters['rate__destination_port_id'] = data.get('destination_id')
    elif data.get('destination_port'):
        query_filters['rate__destination_port'] = data.get('destination_port')

    # نوع کالا
    if data.get('cargo_type'):
        query_filters['rate__cargo_types'] = data.get('cargo_type')

    base_query = RateTier.objects.filter(**query_filters).select_related(
        'rate',
        'rate__forwarder',
        'rate__branch',
        'rate__branch__company'
    ).distinct()

    if is_fcl:
        fcl_filters = {
            'container_size': data.get('container_size')
        }

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
        rate = tier.rate

        # محاسبه نرخ حمل
        if is_fcl:
            count = int(data.get('container_count') or 1)
            base_shipping_price = Decimal(str(tier.price)) * count
            extra_charge_weight = actual_wt
        else:
            if tier.pricing_unit == 'per_kg':
                base_shipping_price = Decimal(str(tier.price)) * cw
            else:
                base_shipping_price = Decimal(str(tier.price))

            extra_charge_weight = cw

        # اگر مشتری بسته‌بندی خواسته باشد، فقط نرخ‌هایی معتبرند که بسته‌بندی ارائه می‌کنند
        if needs_packaging and rate.packaging_charge_type == ExtraChargeType.NOT_AVAILABLE:
            continue

        # اگر مشتری در مرحله تکمیل سفارش، بسته‌بندی و تحویل در محل خواسته باشد،
        # فقط نرخ‌هایی معتبرند که این سرویس را ارائه می‌کنند
        if needs_doorstep_packaging and rate.doorstep_packaging_charge_type == ExtraChargeType.NOT_AVAILABLE:
            continue

        # هزینه بسته‌بندی فقط در صورت انتخاب مشتری لحاظ شود
        if needs_packaging:
            packaging_price = calculate_extra_charge(
                rate.packaging_charge_type,
                rate.packaging_price,
                extra_charge_weight
            )
        else:
            packaging_price = Decimal("0.00")

        # هزینه بسته‌بندی و تحویل در محل فقط در مرحله بعد و در صورت انتخاب مشتری لحاظ شود
        if needs_doorstep_packaging:
            doorstep_packaging_price = calculate_extra_charge(
                rate.doorstep_packaging_charge_type,
                rate.doorstep_packaging_price,
                extra_charge_weight
            )
        else:
            doorstep_packaging_price = Decimal("0.00")

        subtotal = base_shipping_price + packaging_price + doorstep_packaging_price


        if rate.add_vat:
            vat_amount = subtotal * VAT_RATE
        else:
            vat_amount = Decimal("0.00")

        total_price = subtotal + vat_amount

        if rate.forwarder:
            company_name = rate.forwarder.company_name
        elif hasattr(rate, 'branch') and rate.branch:
            company_name = rate.branch.company.company_name
        else:
            company_name = "ناشناس"

        results.append({
            'rate_id': rate.id,
            'company_name': company_name,

            'unit_price': str(money(tier.price)),

            'base_shipping_price': str(money(base_shipping_price)),

            'needs_packaging': needs_packaging,
            'packaging_available': rate.packaging_charge_type != ExtraChargeType.NOT_AVAILABLE,
            'packaging_charge_type': rate.packaging_charge_type,
            'packaging_unit_price': str(money(rate.packaging_price)),
            'packaging_price': str(money(packaging_price)),

            'needs_doorstep_packaging': needs_doorstep_packaging,
            'doorstep_packaging_available': rate.doorstep_packaging_charge_type != ExtraChargeType.NOT_AVAILABLE,
            'doorstep_packaging_charge_type': rate.doorstep_packaging_charge_type,
            'doorstep_packaging_unit_price': str(money(rate.doorstep_packaging_price)),
            'doorstep_packaging_price': str(money(doorstep_packaging_price)),

            'add_vat': rate.add_vat,
            'vat_amount': str(money(vat_amount)),

            'subtotal': str(money(subtotal)),
            'total_price': str(money(total_price)),

            'shipping_procedure': rate.shipping_procedure,
        })


    results = sorted(results, key=lambda x: Decimal(x['total_price']))

    return {
        'actual_weight': str(money(actual_wt)),
        'volumetric_weight': str(money(total_volumetric_weight)),
        'chargeable_weight': str(money(cw)),
        'results': results
    }
