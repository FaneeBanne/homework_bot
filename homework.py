import os
import sys
import time
import logging
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot

from exeptions import (
    ConectionApiError, ResponseError,
    TelegramSendMessageError,
    EmptyHomework
)


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRAC_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TG_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='bot.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)


def check_tokens():
    """Проверка критических переменных."""
    values = {
        'PRACTICUM_TOKEN':PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN':TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID':TELEGRAM_CHAT_ID
    }
    flag = True
    for key, value in values:
        if not value:
            flag = False
            logging.critical(f'Пропущен токен: {key}')
    return flag


def send_message(bot, message):
    """Функция отвечает за отправку сообщения."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        raise TelegramSendMessageError(
            f'Сбой отправки сообщения в телеграм {error}.'
        )
    else:
        logging.debug(f'Сообщения успешно отправлено: {message}.')


def get_api_answer(timestamp):
    """Функция получения ответа от API."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        )

    except Exception:
        raise ConectionApiError(
            f'Ошибка во время запроса к API {ENDPOINT}.'
            f' Параметры: {HEADERS, payload}'
        )
    if homework_statuses.status_code != HTTPStatus.OK:
        raise ResponseError(f'API вернул код {homework_statuses.status_code}')
    homework_statuses.raise_for_status()
    logging.info(
        f'Отправляем запрос к API. Параметры: {ENDPOINT, HEADERS, payload}'
    )
    return homework_statuses.json()


def check_response(response):
    """Проверка на пустоту ответа от API."""
    if not isinstance(response, dict):
        raise TypeError('Ответ не является словарем')
    if 'homeworks' not in response:
        raise KeyError('Не найдеy ключ homeworks')
    if 'current_date' not in response:
        raise KeyError('Не найден ключ current_date')
    homeworks = response['homeworks']
    current_date = response['current_date']

    if not isinstance(homeworks, list):
        raise TypeError('homeworks в ответе API не является списком.')
    if not isinstance(current_date, int):
        raise TypeError('current_date в ответе API не является int.')
    if not homeworks:
        raise EmptyHomework('Пустая домашняя работа')
    return homeworks


def parse_status(homework):
    """Сбор данных с API."""
    if 'status' not in homework: 
        raise KeyError('Не найден ключ status')
    if 'homework_name' not in homework:
        raise KeyError('Не найден ключ homework_name')
    status = homework['status']
    homework_name = homework['homework_name']
    if not homework_name:
        raise KeyError('Пустое значение по ключу')
    if status not in HOMEWORK_VERDICTS:
        raise KeyError('Не корректный статус домашней работы.')

    verdict = HOMEWORK_VERDICTS.get(status)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            'Отсутствует обязательная переменная окружения.')
        sys.exit()

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            status = parse_status(homeworks[0])
            send_message(bot, status)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
