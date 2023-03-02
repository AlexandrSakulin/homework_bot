import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

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
    tokens = (
        ('Практикум токен', PRACTICUM_TOKEN),
        ('Телеграм токен', TELEGRAM_TOKEN),
        ('ID чата', TELEGRAM_TOKEN),
    )
    variables = True
    for name, token in tokens:
        if not token:
            logger.critical(f'Отсутствует {name}')
            variables = False
    return variables


def send_message(bot, message):
    """Отправляет сообщения в чат. Чат определяется по TELEGRAM_CHAT_ID."""
    try:
        logger.debug(f'Начата отправка сообщения: {message}')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(
            f'Сообщение в Telegram отправлено: {message}')
        return True
    except telegram.error.TelegramError as error:
        logger.error(
            f'Сообщение в Telegram не отправлено: {error}')
        return False


def get_api_answer(timestamp):
    """Создает запрос к эндпоинту и возвращает объект домашней работы."""
    params = {'from_date': timestamp}
    response_values = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params,
    }
    logger.debug(
        'Начинаем запрос к API "{url}" с параметрами: '
        '"{params}"'.format(**response_values))
    try:
        response = requests.get(response_values)
        if response.status_code != HTTPStatus.OK:
            message = (f'Ошибка при получении ответа с сервера '
                       f'{response.status_code}: {response.reason}, '
                       f'{response.text}')
            raise EndpointStatusError(message)
        logger.debug('Получен ответ от сервера')
        return response.json()
    except Exception as error:
        raise ConnectionError(
            'Код ответа API к "{url}" с '
            'параметрами: "{params}" (ConnectionError):'
            '{error}'.format(**response_values, error=error))


def check_response(response):
    """Проверяет ответ API на соответствие требованиям."""
    logger.debug('Начата проверка API на кооректность')
    if not isinstance(response, dict):
        raise TypeError('Необрабатываемый ответ API.')
    if 'homeworks' not in response:
        raise exceptions.EmptyAnswersAPI('Пустой ответ от API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Неверные данные.')
    return homeworks


def parse_status(homework):
    """Получает статус конкретной домашней работы."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('У homework нет имени')
    homework_status = homework.get('status')
    if homework_status is None:
        raise KeyError('У homework нет статуса')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Ошибка статуса homework : {homework_status}')
    logging.debug(f'Новый статус {homework_status}')
    return ('Изменился статус проверки работы "{homework_name}". '
            '{verdict}'.format(homework_name=homework_name,
                               verdict=HOMEWORK_VERDICTS.get(homework_status)))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise KeyError('Отсутсвуют необходимые переменные')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    current_report = {}
    prev_report = {}
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                current_report['сообщение'] = message
            if current_report != prev_report:
                if send_message(bot, message):
                    prev_report = current_report.copy()
                    timestamp = response.get('current_date', timestamp)
        except exceptions.EmptyAnswersAPI as error:
            logger.debug(f'Пустой ответ от API: {error}')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            current_report['сообщение'] = message
            logger.exception(message)
            if current_report != prev_report:
                send_message(bot, message)
                prev_report = current_report.copy()
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='logs.log',
        format='%(asctime)s, %(levelname)s, %(message)s,'
               '%(funcName)s, %(lineno)s',
        filemode='a',
    )
    main()
