class WrongResponseCodeError(Exception):
    """Неверный ответ API."""
    pass


class EmptyResponseFromAPIError(Exception):
    """Пустой ответ API."""
    pass


class TelegramError(Exception):
    """Ошибка отправки в Telegram"""
    pass


class EndpointError(Exception):
    """Ошибка Endpoint."""
    pass
