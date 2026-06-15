from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path(
        "orders/<int:order_id>/documents/",
        views.order_documents_step,
        name="order_documents_step"
    ),

    path(
        "orders/documents/<int:document_id>/upload/",
        views.upload_order_document,
        name="upload_order_document"
    ),

    path(
        "orders/<int:order_id>/finalize/",
        views.finalize_order_after_documents,
        name="finalize_order_after_documents"
    ),

    path(
        "additional-upload/<uuid:token>/",
        views.additional_document_upload,
        name="additional_upload"
    ),
    path(
        "order/<int:order_id>/",
        views.order_documents_view,
        name="order_documents"
    )

]
