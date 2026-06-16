from django.db import transaction
from django.db.models import Q

from .models import (
    DocumentRule,
    OrderDocument,
    OrderDocumentStatus,
)


def get_order_destination_country(order):
    """
    استخراج کشور مقصد از سفارش.

    طبق مدل فعلی:
    order.destination_port.city.country
    """

    if not getattr(order, "destination_port_id", None):
        return None

    destination_port = order.destination_port

    if not destination_port:
        return None

    if not getattr(destination_port, "city_id", None):
        return None

    if not destination_port.city:
        return None

    return destination_port.city.country


def get_order_cargo_subcategories(order):
    """
    گرفتن زیردسته‌های کالا از سفارش.
    """

    if not order.pk:
        return []

    return list(order.cargo_subcategories.all())

def rule_matches_order(rule, order, destination_country=None, cargo_subcategories=None):
    """
    بررسی اینکه یک قانون با سفارش فعلی match هست یا نه.

    منطق:
    - اگر یک فیلد در قانون خالی باشد، یعنی آن شرط عمومی است.
    - اگر یک فیلد مقدار داشته باشد، باید دقیقاً با سفارش برابر باشد.
    - قوانین cumulative هستند؛ یعنی قانون اختصاصی‌تر قانون عمومی‌تر را حذف نمی‌کند.
    """

    if destination_country is None:
        destination_country = get_order_destination_country(order)

    if cargo_subcategories is None:
        cargo_subcategories = get_order_cargo_subcategories(order)

    # 1. رویه ارسال
    if rule.shipping_procedure:
        if not getattr(order, "shipping_procedure", None):
            return False

        if rule.shipping_procedure != order.shipping_procedure:
            return False

    # 2. روش حمل
    if rule.transport_mode:
        if not getattr(order, "transport_mode", None):
            return False

        if rule.transport_mode != order.transport_mode:
            return False

    # 3. مبدا - استان
    if getattr(rule, "origin_province_id", None):
        if not getattr(order, "origin_province_id", None):
            return False

        if rule.origin_province_id != order.origin_province_id:
            return False

    # 4. مبدا - شهر
    if getattr(rule, "origin_city_id", None):
        if not getattr(order, "origin_city_id", None):
            return False

        if rule.origin_city_id != order.origin_city_id:
            return False

    # 5. مقصد - کشور
    if rule.destination_country_id:
        if not destination_country:
            return False

        if rule.destination_country_id != destination_country.id:
            return False

    # 6. مقصد - شهر
    if getattr(rule, "destination_city_id", None):
        if not getattr(order, "destination_port_id", None):
            return False

        if not order.destination_port or not order.destination_port.city_id:
            return False

        if rule.destination_city_id != order.destination_port.city_id:
            return False

    # 7. مقصد - پورت/فرودگاه/گمرک
    if getattr(rule, "destination_port_id", None):
        if not getattr(order, "destination_port_id", None):
            return False

        if rule.destination_port_id != order.destination_port_id:
            return False

    # 8. دسته اصلی کالا
    if rule.cargo_type_id:
        if not order.cargo_type_id:
            return False

        if rule.cargo_type_id != order.cargo_type_id:
            return False

    # 9. زیردسته کالا
    if rule.cargo_subcategory_id:
        if not cargo_subcategories:
            return False

        cargo_subcategory_ids = [item.id for item in cargo_subcategories]

        if rule.cargo_subcategory_id not in cargo_subcategory_ids:
            return False

    return True

def get_matching_document_rules(order):
    destination_country = get_order_destination_country(order)
    cargo_subcategories = get_order_cargo_subcategories(order)

    rules = DocumentRule.objects.filter(
        is_active=True,
        document_type__is_active=True,
    ).select_related(
        "document_type",
        "origin_province",
        "origin_city",
        "destination_country",
        "destination_city",
        "destination_port",
        "cargo_type",
        "cargo_subcategory",
    )

    matched_rule_ids = []

    for rule in rules:
        if rule_matches_order(
            rule=rule,
            order=order,
            destination_country=destination_country,
            cargo_subcategories=cargo_subcategories,
        ):
            matched_rule_ids.append(rule.id)

    return DocumentRule.objects.filter(
        id__in=matched_rule_ids
    ).select_related(
        "document_type",
        "origin_province",
        "origin_city",
        "destination_country",
        "destination_city",
        "destination_port",
        "cargo_type",
        "cargo_subcategory",
    ).order_by(
        "-priority",
        "-created_at",
        "document_type__title",
    )


def get_required_document_types_for_order(order):
    """
    خروجی نهایی مدارک موردنیاز برای سفارش.

    نکته مهم:
    این تابع قوانین را حذف نمی‌کند.
    هر قانونی که match باشد، مدرکش موردنیاز است.

    اما چون در مدل OrderDocument محدودیت داریم:

        unique(order, document_type)

    اگر چند قانون مختلف به یک DocumentType یکسان برسند،
    فقط یک OrderDocument برای آن نوع مدرک ساخته می‌شود.

    در چنین حالتی source_rule را اختصاصی‌ترین/مهم‌ترین قانون قرار می‌دهیم.
    """

    rules = get_matching_document_rules(order)

    document_map = {}

    for rule in rules:
        document_type_id = rule.document_type_id

        if document_type_id not in document_map:
            document_map[document_type_id] = rule
            continue

        current_rule = document_map[document_type_id]

        current_score = current_rule.specificity_score + current_rule.priority
        new_score = rule.specificity_score + rule.priority

        if new_score > current_score:
            document_map[document_type_id] = rule

    return document_map


@transaction.atomic
def sync_order_required_documents(order):
    """
    ساخت و همگام‌سازی مدارک موردنیاز سفارش بر اساس قوانین.

    منطق:
    - همه قوانین match شده بررسی می‌شوند.
    - برای هر DocumentType لازم، یک OrderDocument ساخته می‌شود.
    - مدارکی که قبلاً ساخته شده‌اند ولی دیگر طبق قوانین فعلی لازم نیستند:
        اگر فایل ندارند، حذف می‌شوند.
        اگر فایل دارند، اجباری بودنشان برداشته می‌شود تا در تکمیل مدارک مزاحم نباشند.

    این کار باعث می‌شود در صفحه آپلود فقط مدارک مرتبط با سفارش فعلی نمایش داده شوند.
    """

    document_map = get_required_document_types_for_order(order)

    required_document_type_ids = set(document_map.keys())

    current_documents = []

    for document_type_id, rule in document_map.items():
        order_document, created = OrderDocument.objects.get_or_create(
            order=order,
            document_type_id=document_type_id,
            defaults={
                "source_rule": rule,
                "is_required": rule.is_required,
                "status": OrderDocumentStatus.PENDING_UPLOAD,
            }
        )

        if not created:
            changed = False

            if order_document.source_rule_id != rule.id:
                order_document.source_rule = rule
                changed = True

            if order_document.is_required != rule.is_required:
                order_document.is_required = rule.is_required
                changed = True

            # اگر قبلاً reject شده بوده و مشتری دوباره وارد مرحله مدارک شده،
            # وضعیت را دست نمی‌زنیم مگر اینکه فایل نداشته باشد.
            if not order_document.file and order_document.status != OrderDocumentStatus.PENDING_UPLOAD:
                order_document.status = OrderDocumentStatus.PENDING_UPLOAD
                changed = True

            if changed:
                order_document.save(update_fields=[
                    "source_rule",
                    "is_required",
                    "status",
                    "updated_at",
                ])

        current_documents.append(order_document)

    # مدارکی که قبلاً برای این سفارش ساخته شده‌اند
    # ولی الان طبق قوانین فعلی دیگر لازم نیستند.
    stale_documents = OrderDocument.objects.filter(
        order=order
    ).exclude(
        document_type_id__in=required_document_type_ids
    )

    for stale_doc in stale_documents:
        # اگر فایل ندارد، حذف شود چون دیگر لازم نیست.
        if not stale_doc.file:
            stale_doc.delete()
            continue

        # اگر فایل دارد، حذفش نمی‌کنیم تا دیتای کاربر از بین نرود.
        # فقط از حالت اجباری خارج می‌کنیم.
        if stale_doc.is_required:
            stale_doc.is_required = False
            stale_doc.save(update_fields=[
                "is_required",
                "updated_at",
            ])

    return current_documents


def get_current_order_documents_queryset(order):
    """
    گرفتن فقط مدارکی که طبق قوانین فعلی سفارش لازم هستند.

    این تابع برای نمایش در template استفاده شود،
    نه اینکه همه OrderDocumentهای سفارش نمایش داده شوند.
    """

    document_map = get_required_document_types_for_order(order)

    required_document_type_ids = set(document_map.keys())

    return OrderDocument.objects.select_related(
        "document_type",
        "source_rule",
    ).filter(
        order=order,
        document_type_id__in=required_document_type_ids,
    ).order_by(
        "document_type__title"
    )


def get_order_documents_status(order):
    """
    وضعیت تکمیل مدارک سفارش.

    فقط مدارکی بررسی می‌شوند که طبق قوانین فعلی سفارش لازم هستند.
    """

    document_map = get_required_document_types_for_order(order)

    required_document_type_ids = set(document_map.keys())

    required_documents = OrderDocument.objects.filter(
        order=order,
        document_type_id__in=required_document_type_ids,
        is_required=True,
    )

    total_required = required_documents.count()

    uploaded_required = required_documents.exclude(
        file=""
    ).exclude(
        file__isnull=True
    ).count()

    missing_documents = required_documents.filter(
        Q(file="") | Q(file__isnull=True)
    )

    return {
        "total_required": total_required,
        "uploaded_required": uploaded_required,
        "missing_count": missing_documents.count(),
        "missing_documents": missing_documents,
        "is_complete": total_required == uploaded_required,
    }


def order_has_all_required_documents(order):
    """
    بررسی اینکه همه مدارک اجباری فعلی سفارش آپلود شده‌اند یا نه.
    """

    status = get_order_documents_status(order)
    return status["is_complete"]
