class ConectionApiError(Exception):
    """Ошибка подключения к API."""

class ResponseError(Exception):
    """Ошибка статус кода от API."""

class TelegramSendMessageError(Exception):
    """Ошибка отправки сообщения в телеграм"""

class EmptyHomework(Exception):
    """Список homework пустой"""