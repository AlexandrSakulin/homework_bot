class StatusError(Exception):
    """Неверный статус работы в ответе API"""


class EndpointStatusError(Exception):
    """Возникла проблема с удаленным сервером."""


class EndpointNotAnswer(Exception):
    """Удаленный сервер не отвечает"""


class EmptyAnswersAPI(Exception):
    """Пустой ответ API."""
