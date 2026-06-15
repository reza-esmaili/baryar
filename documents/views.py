from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from orders.models import CargoRequest, OrderStatus
from orders.models import OrderHistory

from .forms import (
    OrderDocumentUploadForm,
    AdditionalDocumentUploadForm,
)
from .models import (
    OrderDocument,
    OrderDocumentStatus,
    AdditionalDocumentRequest,
    AdditionalRequestStatus,
    AdditionalDocumentUpload,
)
from .services import (
    sync_order_required_documents,
    get_order_documents_status,
    order_has_all_required_documents,
)

@login_required
def order_documents_view(request, order_id):

    order = get_object_or_404(
        CargoRequest,
        id=order_id,
        customer=request.user
    )

    documents = order.required_documents.select_related("document_type")

    if request.method == "POST":

        for doc in documents:

            uploaded_file = request.FILES.get(f"doc_{doc.id}")

            if uploaded_file:
                doc.file = uploaded_file
                doc.mark_uploaded(request.user)

        # بررسی کامل بودن مدارک
        remaining = documents.filter(
            is_required=True,
            status=OrderDocumentStatus.PENDING_UPLOAD
        ).exists()

        if not remaining:
            order.status = OrderStatus.PENDING
            order.save(update_fields=["status"])

        return redirect("customer:order_detail", pk=order.id)

    return render(
        request,
        "documents/order_documents.html",
        {
            "order": order,
            "documents": documents,
        }
    )

@login_required
def order_documents_step(request, order_id):
    """
    صفحه آپلود مدارک سفارش قبل از ثبت نهایی.

    کاربر باید تمام مدارک اجباری را آپلود کند.
    """

    order = get_object_or_404(
        CargoRequest.objects.select_related(
            "customer",
            "origin_city",
            "destination_port",
            "destination_port__city",
            "destination_port__city__country",
            "cargo_type",
        ).prefetch_related(
            "cargo_subcategories"
        ),
        id=order_id,
        customer=request.user,
    )

    if order.status != OrderStatus.DRAFT:
        messages.warning(request, "مدارک این سفارش در این مرحله قابل ویرایش نیست.")
        return redirect("customer:order_detail", order.id)

    sync_order_required_documents(order)

    documents = OrderDocument.objects.select_related(
        "document_type",
        "source_rule",
    ).filter(
        order=order
    ).order_by("document_type__title")

    documents_status = get_order_documents_status(order)

    return render(request, "documents/order_documents.html", {
        "order": order,
        "documents": documents,
        "documents_status": documents_status,
    })


@login_required
def upload_order_document(request, document_id):
    """
    آپلود یک مدرک خاص از مدارک سفارش.
    """

    order_document = get_object_or_404(
        OrderDocument.objects.select_related(
            "order",
            "order__customer",
            "document_type",
        ),
        id=document_id,
        order__customer=request.user,
    )

    order = order_document.order

    if order.status != OrderStatus.DRAFT:
        messages.error(request, "امکان ویرایش مدارک در این وضعیت وجود ندارد.")
        return redirect("documents:order_documents_step", order.id)

    if request.method != "POST":
        raise Http404

    form = OrderDocumentUploadForm(
        request.POST,
        request.FILES,
        instance=order_document
    )

    if form.is_valid():
        document = form.save(commit=False)
        document.uploaded_by = request.user
        document.status = OrderDocumentStatus.UPLOADED
        document.rejection_reason = ""
        document.save()

        messages.success(request, "مدرک با موفقیت آپلود شد.")
    else:
        messages.error(request, "خطا در آپلود مدرک. لطفاً نوع و حجم فایل را بررسی کنید.")

    return redirect("documents:order_documents_step", order.id)


@login_required
@transaction.atomic
def finalize_order_after_documents(request, order_id):
    """
    ثبت نهایی سفارش بعد از تکمیل مدارک.

    اگر مدارک اجباری کامل نباشند، سفارش نهایی نمی‌شود.
    """

    order = get_object_or_404(
        CargoRequest.objects.select_related("customer"),
        id=order_id,
        customer=request.user,
    )

    if order.status != OrderStatus.DRAFT:
        messages.warning(request, "این سفارش قبلاً از حالت پیش‌نویس خارج شده است.")
        return redirect("customer:order_detail", order.id)

    sync_order_required_documents(order)

    if not order_has_all_required_documents(order):
        messages.error(request, "برای ثبت نهایی سفارش، ابتدا باید تمام مدارک اجباری را آپلود کنید.")
        return redirect("documents:order_documents_step", order.id)

    order.status = OrderStatus.PENDING
    order.save(update_fields=["status", "updated_at"])

    OrderHistory.objects.create(
        order=order,
        changed_by=request.user,
        field_name="status",
        old_value=OrderStatus.DRAFT,
        new_value=OrderStatus.PENDING,
        note="سفارش پس از تکمیل مدارک توسط مشتری ثبت نهایی شد."
    )

    messages.success(request, "سفارش شما با موفقیت ثبت نهایی شد و در انتظار تایید فورواردر قرار گرفت.")
    return redirect("customer:order_detail", order.id)


def additional_document_upload(request, token):
    """
    صفحه عمومی/نیمه‌عمومی آپلود مدرک تکمیلی با لینک اختصاصی.

    این صفحه می‌تواند بدون login هم کار کند.
    اما اگر مشتری لاگین بود، uploaded_by ثبت می‌شود.
    """

    additional_request = get_object_or_404(
        AdditionalDocumentRequest.objects.select_related(
            "order",
            "order__customer",
            "document_type",
        ),
        token=token,
    )

    if additional_request.status in [
        AdditionalRequestStatus.CANCELLED,
        AdditionalRequestStatus.COMPLETED,
    ]:
        return render(request, "documents/additional_upload.html", {
            "additional_request": additional_request,
            "form": None,
            "is_closed": True,
            "message": "این درخواست قبلاً بسته شده است.",
        })

    if additional_request.is_expired:
        additional_request.status = AdditionalRequestStatus.EXPIRED
        additional_request.save(update_fields=["status", "updated_at"])

        return render(request, "documents/additional_upload.html", {
            "additional_request": additional_request,
            "form": None,
            "is_closed": True,
            "message": "مهلت آپلود این مدرک به پایان رسیده است.",
        })

    if request.method == "POST":
        form = AdditionalDocumentUploadForm(request.POST, request.FILES)

        if form.is_valid():
            upload = form.save(commit=False)
            upload.request = additional_request

            if request.user.is_authenticated:
                upload.uploaded_by = request.user

            upload.save()

            additional_request.status = AdditionalRequestStatus.COMPLETED
            additional_request.save(update_fields=["status", "updated_at"])

            OrderHistory.objects.create(
                order=additional_request.order,
                changed_by=request.user if request.user.is_authenticated else None,
                note=f"مدرک تکمیلی '{additional_request.document_title}' توسط مشتری آپلود شد."
            )

            messages.success(request, "مدرک با موفقیت ارسال شد.")

            return render(request, "documents/additional_upload.html", {
                "additional_request": additional_request,
                "form": None,
                "is_closed": True,
                "message": "مدرک شما با موفقیت دریافت شد.",
            })
    else:
        form = AdditionalDocumentUploadForm()

    return render(request, "documents/additional_upload.html", {
        "additional_request": additional_request,
        "form": form,
        "is_closed": False,
        "message": "",
    })
