from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string

from .models import (
    Ticket,
    TicketMessage,
    TicketTopic,
    TicketActivity,
    TicketTransfer,
    SupportAgent,
    SupportDepartment,
)
from .forms import TicketCreateForm, TicketReplyForm, TicketTransferForm


def is_forwarder_user(user):
    return hasattr(user, "forwardercompany")


def get_panel_type(request):
    """
    تشخیص می‌دهد کاربر از پنل فورواردر وارد شده یا پنل مشتری.
    """
    path = request.path

    if path.startswith("/forwarder/support/"):
        return "forwarder"

    if path.startswith("/customer/profile/support/"):
        return "customer"

    if is_forwarder_user(request.user):
        return "forwarder"

    return "customer"


def get_template_path(request, template_name):
    panel_type = get_panel_type(request)

    if panel_type == "forwarder":
        return f"forwarder_panel/support/{template_name}"

    return f"customer_panel/profile/support/{template_name}"


def get_partial_template_path(request, template_name):
    panel_type = get_panel_type(request)

    if panel_type == "forwarder":
        return f"forwarder_panel/support/partials/{template_name}"

    return f"customer_panel/profile/support/partials/{template_name}"


def get_list_url_name(request):
    panel_type = get_panel_type(request)

    if panel_type == "forwarder":
        return "forwarder_support:ticket_list"

    return "customer_support:ticket_list"


def get_detail_url_name(request):
    panel_type = get_panel_type(request)

    if panel_type == "forwarder":
        return "forwarder_support:ticket_detail"

    return "customer_support:ticket_detail"


def get_create_url_name(request):
    panel_type = get_panel_type(request)

    if panel_type == "forwarder":
        return "forwarder_support:ticket_create"

    return "customer_support:ticket_create"


def get_transfer_url_name(request):
    panel_type = get_panel_type(request)

    if panel_type == "forwarder":
        return "forwarder_support:ticket_transfer"

    return "customer_support:ticket_transfer"


def auto_assign_agent(ticket):
    """
    تخصیص خودکار کارشناس از واحد انتخاب‌شده
    """
    agents = SupportAgent.objects.filter(
        departments=ticket.department,
        is_active=True
    ).order_by("id")

    if agents.exists() and not ticket.assigned_agent:
        ticket.assigned_agent = agents.first()
        ticket.save(update_fields=["assigned_agent"])


@login_required
def ticket_list(request):
    panel_type = get_panel_type(request)

    tickets = Ticket.objects.filter(
        user=request.user,
        department__panel_type=panel_type
    ).select_related(
        "department", "topic", "assigned_agent"
    ).order_by("-updated_at", "-created_at")

    department = request.GET.get("department")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    q = request.GET.get("q")

    if department:
        tickets = tickets.filter(department_id=department)

    if date_from:
        tickets = tickets.filter(created_at__date__gte=date_from)

    if date_to:
        tickets = tickets.filter(created_at__date__lte=date_to)

    if q:
        tickets = tickets.filter(subject__icontains=q)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string(
            get_partial_template_path(request, "ticket_rows.html"),
            {"tickets": tickets},
            request=request
        )
        return JsonResponse({"html": html})

    departments = SupportDepartment.objects.filter(
        is_active=True,
        panel_type=panel_type
    )

    return render(
        request,
        get_template_path(request, "ticket_list.html"),
        {
            "tickets": tickets,
            "departments": departments,
            "panel_type": panel_type,
            "create_url_name": get_create_url_name(request),
        }
    )


@login_required
def ticket_create(request):
    panel_type = get_panel_type(request)

    if request.method == "POST":
        form = TicketCreateForm(
            request.POST,
            request.FILES,
            panel_type=panel_type
        )

        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.unread_for_agent = True
            ticket.unread_for_user = False
            ticket.status = Ticket.Status.OPEN
            ticket.save()

            TicketMessage.objects.create(
                ticket=ticket,
                sender=request.user,
                message=form.cleaned_data["message"],
                attachment=request.FILES.get("attachment")
            )

            TicketActivity.objects.create(
                ticket=ticket,
                user=request.user,
                action="تیکت جدید ایجاد شد"
            )

            auto_assign_agent(ticket)

            messages.success(request, "تیکت شما با موفقیت ثبت شد.")
            return redirect(get_detail_url_name(request), pk=ticket.pk)

    else:
        form = TicketCreateForm(panel_type=panel_type)

    return render(
        request,
        get_template_path(request, "ticket_create.html"),
        {
            "form": form,
            "list_url_name": get_list_url_name(request),
        }
    )


@login_required
def ticket_detail(request, pk):
    panel_type = get_panel_type(request)

    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "department", "topic", "assigned_agent", "user"
        ).prefetch_related(
            "messages", "activities", "transfers"
        ),
        pk=pk,
        department__panel_type=panel_type
    )

    if ticket.user != request.user:
        try:
            support_agent = request.user.supportagent
            if not support_agent.departments.filter(
                id=ticket.department_id,
                panel_type=panel_type
            ).exists():
                return HttpResponseForbidden("شما اجازه دسترسی به این تیکت را ندارید.")
        except SupportAgent.DoesNotExist:
            return HttpResponseForbidden("شما اجازه دسترسی به این تیکت را ندارید.")

    messages_qs = ticket.messages.all().order_by("created_at")
    activities = ticket.activities.all().order_by("-created_at")
    transfer_form = None

    try:
        support_agent = request.user.supportagent
        if support_agent.departments.filter(
            id=ticket.department_id,
            panel_type=panel_type
        ).exists():
            transfer_form = TicketTransferForm()
            transfer_form.fields["to_department"].queryset = SupportDepartment.objects.filter(
                is_active=True,
                panel_type=panel_type
            ).exclude(id=ticket.department_id)
    except SupportAgent.DoesNotExist:
        pass

    if request.method == "POST":
        form = TicketReplyForm(request.POST, request.FILES)

        if form.is_valid():
            reply = form.save(commit=False)
            reply.ticket = ticket
            reply.sender = request.user
            reply.save()

            if ticket.user == request.user:
                ticket.unread_for_agent = True
                ticket.unread_for_user = False
                ticket.status = Ticket.Status.OPEN
                activity_text = "کاربر پاسخ جدید ثبت کرد"
            else:
                ticket.unread_for_user = True
                ticket.unread_for_agent = False
                ticket.status = Ticket.Status.ANSWERED
                activity_text = "کارشناس پاسخ جدید ثبت کرد"

            ticket.save(update_fields=["unread_for_agent", "unread_for_user", "status", "updated_at"])

            TicketActivity.objects.create(
                ticket=ticket,
                user=request.user,
                action=activity_text
            )

            messages.success(request, "پاسخ شما ثبت شد.")
            return redirect(get_detail_url_name(request), pk=ticket.pk)

    else:
        form = TicketReplyForm()

    if ticket.user == request.user and ticket.unread_for_user:
        ticket.unread_for_user = False
        ticket.save(update_fields=["unread_for_user", "updated_at"])

    return render(
        request,
        get_template_path(request, "ticket_detail.html"),
        {
            "ticket": ticket,
            "messages": messages_qs,
            "activities": activities,
            "form": form,
            "transfer_form": transfer_form,
            "list_url_name": get_list_url_name(request),
            "transfer_url_name": get_transfer_url_name(request),
        }
    )


@login_required
def load_topics(request):
    panel_type = get_panel_type(request)
    department_id = request.GET.get("department_id")

    if not department_id:
        return JsonResponse({"topics": []})

    topics_qs = TicketTopic.objects.filter(
        department_id=department_id,
        department__panel_type=panel_type,
        department__is_active=True,
        is_active=True
    )

    data = []
    for topic in topics_qs:
        name = getattr(topic, "name", getattr(topic, "title", str(topic)))
        data.append({
            "id": topic.id,
            "name": name
        })

    return JsonResponse({"topics": data})


@login_required
def agent_dashboard(request):
    panel_type = get_panel_type(request)

    try:
        agent = request.user.supportagent
    except SupportAgent.DoesNotExist:
        return HttpResponseForbidden("شما کارشناس پشتیبانی نیستید.")

    tickets = Ticket.objects.filter(
        department__in=agent.departments.filter(panel_type=panel_type),
        department__panel_type=panel_type
    ).select_related(
        "user", "department", "topic", "assigned_agent"
    ).order_by("-updated_at", "-created_at")

    return render(
        request,
        "support/agent_dashboard.html",
        {
            "tickets": tickets,
            "agent": agent,
        }
    )


@login_required
def ticket_transfer(request, pk):
    panel_type = get_panel_type(request)

    ticket = get_object_or_404(
        Ticket,
        pk=pk,
        department__panel_type=panel_type
    )

    try:
        agent = request.user.supportagent
    except SupportAgent.DoesNotExist:
        return HttpResponseForbidden("شما اجازه ارجاع این تیکت را ندارید.")

    if not agent.departments.filter(id=ticket.department_id, panel_type=panel_type).exists():
        return HttpResponseForbidden("شما اجازه ارجاع این تیکت را ندارید.")

    if request.method != "POST":
        return redirect(get_detail_url_name(request), pk=ticket.pk)

    form = TicketTransferForm(request.POST)
    form.fields["to_department"].queryset = SupportDepartment.objects.filter(
        is_active=True,
        panel_type=panel_type
    ).exclude(id=ticket.department_id)

    if form.is_valid():
        old_department = ticket.department
        new_department = form.cleaned_data["to_department"]

        TicketTransfer.objects.create(
            ticket=ticket,
            from_department=old_department,
            to_department=new_department,
            transferred_by=request.user,
            note=form.cleaned_data.get("note", "")
        )

        ticket.department = new_department
        ticket.assigned_agent = None
        ticket.unread_for_agent = True
        ticket.status = Ticket.Status.OPEN
        ticket.save(update_fields=["department", "assigned_agent", "unread_for_agent", "status", "updated_at"])

        auto_assign_agent(ticket)

        TicketActivity.objects.create(
            ticket=ticket,
            user=request.user,
            action=f"تیکت از واحد «{old_department.name}» به واحد «{new_department.name}» ارجاع شد"
        )

        messages.success(request, "تیکت با موفقیت ارجاع شد.")

    return redirect(get_detail_url_name(request), pk=ticket.pk)
