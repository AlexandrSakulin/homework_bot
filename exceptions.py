class StatusError(Exception):
    """Неверный статус работы в ответе API"""
    pass


class EndpointStatusError(Exception):
    """Возникла проблема с удаленным сервером."""
    pass


class EndpointNotAnswer(Exception):
    """Удаленный сервер не отвечает"""
    pass


class EmptyAnswersAPI(Exception):
    """Пустой ответ API."""
    pass


class InvalidResponseCode(Exception):
    """Не верный код ответа"""
    pass
