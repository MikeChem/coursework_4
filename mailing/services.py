from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

from config.settings import CACHE_ENABLED

from .models import Mailing, MailingAttempt, Message, Recipient


def send_email(recipient_email, subject, body):
    """
    Отправляет email-сообщение получателю.

    :param recipient_email: Email адрес получателя
    :param subject: Тема письма
    :param body: Тело письма
    :return: Кортеж (успешно: bool, ответ сервера: str)
    """
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient_email])
        return True, None
    except Exception as e:
        return False, str(e)


def perform_mailing(mailing_id):
    """
    Выполняет рассылку по указанному ID.

    :param mailing_id: ID рассылки
    """
    try:
        mailing = Mailing.objects.get(id=mailing_id)
        if mailing.status == "completed":
            return  # Если рассылка уже завершена, ничего не делаем

        mailing.status = "started"
        mailing.save()

        for recipient in mailing.recipients.all():
            success, response = send_email(recipient.email, mailing.message.subject, mailing.message.body)
            MailingAttempt.objects.create(
                status="success" if success else "failed",
                server_response=response if not success else None,
                mailing=mailing,
            )

        mailing.status = "completed"
        mailing.save()
    except Exception as e:
        print(f"Error during mailing: {e}")


def get_recipients_from_cache():
    if not CACHE_ENABLED:
        return Recipient.objects.all()
    key = "recipient_list"
    recipients = cache.get(key)
    if recipients is not None:
        return recipients
    recipients = Recipient.objects.all()
    cache.set(key, recipients)
    return recipients


def get_messages_from_cache():
    if not CACHE_ENABLED:
        return Message.objects.all()
    key = "message_list"
    messages = cache.get(key)
    if messages is not None:
        return messages
    messages = Message.objects.all()
    cache.set(key, messages)
    return messages
