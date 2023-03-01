import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import EndpointNotAnswer, EndpointStatusError, StatusError

load_dotenv()
logger = logging.getLogger(__name__)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщения в чат. Чат определяется по TELEGRAM_CHAT_ID."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(
            f'Сообщение в Telegram отправлено: {message}')
    except Exception as error:
        logger.error(
            f'Сообщение в Telegram не отправлено: {error}')


def get_api_answer(timestamp):
    """Создает запрос к эндпоинту и возвращает объект домашней работы."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            message = (
                f'Ресурс {ENDPOINT} недоступен. '
                f'Код ответа: {response.status_code}.'
            )
            logger.error(message)
            raise EndpointStatusError
        return response.json()
    except Exception as error:
        raise EndpointNotAnswer(error)


def check_response(response):
    """Проверяет ответ API на соответствие требованиям."""
    if not isinstance(response, dict):
        error_message = 'Необрабатываемый ответ API.'
        logger.error(error_message)
        raise TypeError(error_message)
    if 'homeworks' not in response:
        error_message = 'Ошибка в ответе API, ключ homeworks не найден.'
        logger.error(error_message)
        raise KeyError(error_message)
    if not isinstance(response['homeworks'], list):
        error_message = 'Неверные данные.'
        logger.error(error_message)
        raise TypeError(error_message)
    if not response['homeworks']:
        logger.info('Словарь homeworks пуст.')
        return {}
    return response['homeworks'][0]


def parse_status(homework):
    """Получает статус конкретной домашней работы."""
    if 'homework_name' not in homework:
        error_message = 'Ключ homework_name отсутствует.'
        logger.error(error_message)
        raise KeyError(error_message)
    if 'status' not in homework:
        error_message = 'Ключ status отсутствует.'
        logger.error(error_message)
        raise StatusError()
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        error_message = ('Не определен статус домашней работы!')
        logger.error(error_message)
        raise StatusError()
    else:
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_message = 'Отсутсвуют необходимые переменные'
        logger.critical(error_message)
        raise sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                if message:
                    send_message(bot, message)
            logger.info('Повторение запроса через 10 мин.')
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error(message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('program.log', encoding='UTF-8'),
        ],
    )
    main()
