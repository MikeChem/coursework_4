from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from .forms import MailingForm, MessageForm, RecipientForm
from .models import Mailing, MailingAttempt, Message, Recipient
from .services import get_messages_from_cache, get_recipients_from_cache, perform_mailing

# Контроллеры для получателей рассылки (Recipients)


class RecipientListView(LoginRequiredMixin, ListView):
    model = Recipient
    template_name = "mailing/recipient_list.html"
    context_object_name = "recipients"

    def get_queryset(self):
        return get_recipients_from_cache


class RecipientDetailView(LoginRequiredMixin, DetailView):
    model = Recipient
    template_name = "mailing/recipient_detail.html"
    context_object_name = "recipient"


class RecipientCreateView(LoginRequiredMixin, CreateView):
    model = Recipient
    form_class = RecipientForm
    template_name = "mailing/recipient_form.html"
    success_url = reverse_lazy("recipient_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user  # Установка владельца
        return super().form_valid(form)


class RecipientUpdateView(LoginRequiredMixin, UpdateView):
    model = Recipient
    form_class = RecipientForm
    template_name = "mailing/recipient_form.html"
    success_url = reverse_lazy("recipient_list")


class RecipientDeleteView(LoginRequiredMixin, DeleteView):
    model = Recipient
    template_name = "mailing/recipient_confirm_delete.html"
    success_url = reverse_lazy("recipient_list")


# Контроллеры для сообщений (Messages)


class MessageListView(LoginRequiredMixin, ListView):
    model = Message
    template_name = "mailing/message_list.html"
    context_object_name = "messages"

    def get_queryset(self):
        return get_messages_from_cache


class MessageDetailView(LoginRequiredMixin, DetailView):
    model = Message
    template_name = "mailing/message_detail.html"
    context_object_name = "message"


class MessageCreateView(LoginRequiredMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = "mailing/message_form.html"
    success_url = reverse_lazy("message_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user  # Установка владельца
        return super().form_valid(form)


class MessageUpdateView(LoginRequiredMixin, UpdateView):
    model = Message
    form_class = MessageForm
    template_name = "mailing/message_form.html"
    success_url = reverse_lazy("message_list")


class MessageDeleteView(LoginRequiredMixin, DeleteView):
    model = Message
    template_name = "mailing/message_confirm_delete.html"
    success_url = reverse_lazy("message_list")


# Контроллеры для рассылок (Mailings)


class MailingListView(LoginRequiredMixin, ListView):
    model = Mailing
    template_name = "mailing/mailing_list.html"
    context_object_name = "mailings"

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:  # Менеджеры видят все рассылки
            return Mailing.objects.all()
        else:  # Обычные пользователи видят только свои рассылки
            return Mailing.objects.filter(owner=user)


class MailingDetailView(LoginRequiredMixin, DetailView):
    model = Mailing
    template_name = "mailing/mailing_detail.html"
    context_object_name = "mailing"

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Mailing.objects.all()
        return Mailing.objects.filter(owner=user)


class MailingCreateView(LoginRequiredMixin, CreateView):
    model = Mailing
    form_class = MailingForm
    template_name = "mailing/mailing_form.html"
    success_url = reverse_lazy("mailing_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user  # Установка владельца
        return super().form_valid(form)


class MailingUpdateView(LoginRequiredMixin, UpdateView):
    model = Mailing
    form_class = MailingForm
    template_name = "mailing/mailing_form.html"
    success_url = reverse_lazy("mailing_list")

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Mailing.objects.all()
        return Mailing.objects.filter(owner=user)

    def dispatch(self, request, *args, **kwargs):
        mailing = self.get_object()
        if not self.request.user.is_staff and mailing.owner != self.request.user:
            return HttpResponseForbidden("Вы не имеете прав для редактирования этой рассылки.")
        return super().dispatch(request, *args, **kwargs)


class MailingDeleteView(LoginRequiredMixin, DeleteView):
    model = Mailing
    template_name = "mailing/mailing_confirm_delete.html"
    success_url = reverse_lazy("mailing_list")

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Mailing.objects.all()
        return Mailing.objects.filter(owner=user)

    def dispatch(self, request, *args, **kwargs):
        mailing = self.get_object()
        if not self.request.user.is_staff and mailing.owner != self.request.user:
            return HttpResponseForbidden("Вы не имеете прав для удаления этой рассылки.")
        return super().dispatch(request, *args, **kwargs)


def send_mailing(request, mailing_id):
    if request.method == "POST":
        perform_mailing(mailing_id)  # Вызов функции отправки рассылки
    return redirect("mailing:mailing_list")


class UserStatsView(LoginRequiredMixin, TemplateView):
    template_name = "mailing/user_stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Подсчет успешных и неуспешных попыток
        successful_attempts = MailingAttempt.objects.filter(mailing__owner=user, status="success").count()

        failed_attempts = MailingAttempt.objects.filter(mailing__owner=user, status="failed").count()

        # Общее количество отправленных сообщений
        total_messages_sent = MailingAttempt.objects.filter(mailing__owner=user, status="success").count()

        context.update(
            {
                "successful_attempts": successful_attempts,
                "failed_attempts": failed_attempts,
                "total_messages_sent": total_messages_sent,
            }
        )
        return context


def toggle_mailing_status(request, mailing_id):
    if not request.user.is_staff:
        return HttpResponseForbidden("У вас нет прав для выполнения этого действия.")

    mailing = get_object_or_404(Mailing, id=mailing_id)
    mailing.status = "completed" if mailing.status != "completed" else "created"
    mailing.save()
    return redirect("mailing_list")


class HomeView(LoginRequiredMixin, ListView):
    model = Mailing  # Указывает модель, с которой работает представление
    template_name = "mailing/home.html"  # Имя шаблона
    context_object_name = "mailings"  # Имя переменной в контексте
    login_url = "users:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_mailings"] = Mailing.objects.count()
        context["active_mailings"] = Mailing.objects.filter(status="started").count()
        context["unique_recipients"] = Recipient.objects.count()

        if self.request.user.is_authenticated:
            context["latest_mailings"] = Mailing.objects.filter(owner=self.request.user).order_by("-start_time")[:5]
        else:
            context["latest_mailings"] = []  # Для незарегистрированных пользователей

        return context


class MailingAttemptListView(LoginRequiredMixin, ListView):
    model = MailingAttempt
    template_name = "mailing/mailing_attempt_list.html"
    context_object_name = "attempts"

    def get_queryset(self):
        return MailingAttempt.objects.filter(mailing__owner=self.request.user)


class MailingReportView(LoginRequiredMixin, ListView):
    model = Mailing
    template_name = "mailing/mailing_report.html"
    context_object_name = "mailings"

    def get_queryset(self):
        return Mailing.objects.filter(owner=self.request.user)
