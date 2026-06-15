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
    طبق مدل‌های فعلی شما:
    order.destination_port.city.country
    """
    if not order.destination_port_id:
        return None

    if not order.destination_port.city_id:
        return None

    return order.destination_port.city.country


def get_order_cargo_subcategories(order):
    """
    گرفتن زیردسته‌های کالا از سفارش.
    """
    if not order.pk:
        return []

    return list(order.cargo_subcategories.all())


def get_matching_document_rules(order):
    """
    گرفتن تمام قوانین مدارک منطبق با سفارش.

    منطق:
    اگر فیلد در قانون خالی باشد یعنی عمومی است.
    اگر مقدار داشته باشد باید با سفارش match شود.
    """

    destination_country = get_order_destination_country(order)
    cargo_subcategories = get_order_cargo_subcategories(order)

    rules = DocumentRule.objects.filter(
        is_active=True,
        document_type__is_active=True,
    ).select_related(
        "document_type",
        "destination_country",
        "cargo_type",
        "cargo_subcategory",
    )

    rules = rules.filter(
        Q(shipping_procedure__isnull=True) |
        Q(shipping_procedure="") |
        Q(shipping_procedure=order.shipping_procedure),

        Q(transport_mode__isnull=True) |
        Q(transport_mode="") |
        Q(transport_mode=order.transport_mode),

        Q(destination_country__isnull=True) |
        Q(destination_country=destination_country),

        Q(cargo_type__isnull=True) |
        Q(cargo_type=order.cargo_type),
    )

    if cargo_subcategories:
        rules = rules.filter(
            Q(cargo_subcategory__isnull=True) |
            Q(cargo_subcategory__in=cargo_subcategories)
        )
    else:
        rules = rules.filter(cargo_subcategory__isnull=True)

    return rules.order_by("-priority", "-created_at")


def get_required_document_types_for_order(order):
    """
    خروجی نهایی مدارک موردنیاز برای سفارش.

    اگر چند قانون به یک DocumentType برسند، فقط یک مدرک لازم است.
    اما source_rule را اختصاصی‌ترین قانون در نظر می‌گیریم.
    """

    rules = get_matching_document_rules(order)

    document_map = {}

    for rule in rules:
        doc_id = rule.document_type_id

        if doc_id not in document_map:
            document_map[doc_id] = rule
            continue

        current_rule = document_map[doc_id]

        current_score = current_rule.specificity_score + current_rule.priority
        new_score = rule.specificity_score + rule.priority

        if new_score > current_score:
            document_map[doc_id] = rule

    return document_map


@transaction.atomic
def sync_order_required_documents(order):
    """
    مدارک موردنیاز سفارش را بر اساس قوانین می‌سازد.

    این تابع باید قبل از ورود کاربر به مرحله آپلود مدارک صدا زده شود.
    """

    document_map = get_required_document_types_for_order(order)

    required_document_ids = set(document_map.keys())

    created_or_existing_documents = []

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

            if changed:
                order_document.save(update_fields=[
                    "source_rule",
                    "is_required",
                    "updated_at",
                ])

        created_or_existing_documents.append(order_document)

    # مدارکی که قبلاً لازم بوده ولی الان طبق قوانین لازم نیستند را حذف نمی‌کنیم
    # چون ممکن است فایل آپلود شده باشد و نباید دیتا از بین برود.
    # اگر خواستی می‌توانی اینجا آن‌ها را optional یا inactive کنی.

    return created_or_existing_documents


def get_order_documents_status(order):
    """
    وضعیت تکمیل مدارک سفارش.
    """

    required_documents = OrderDocument.objects.filter(
        order=order,
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
    status = get_order_documents_status(order)
    return status["is_complete"]
