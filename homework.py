import os
import requests
import logging
import sys
import time

from dotenv import load_dotenv
from telebot import TeleBot

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
    values = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    names = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    for value, name in zip(values, names):
        if not value:
            logging.critical(
                f'Отсутствует обязательная переменная окружения: {name}')
            sys.exit()


def send_message(bot, message):
    """Функция отвечает за отправку сообщения."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        raise Exception(f'Сбой отправки сообщения в телеграм {error}.')
    else:
        logging.debug(f'Сообщения успешно отправлено: {message}.')


def get_api_answer(timestamp):
    """Функция получения ответа от API."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        )
        if homework_statuses.status_code != 200:
            raise ValueError(f'API вернул код {homework_statuses.status_code}')
        homework_statuses.raise_for_status()
        logging.info(
            f'Отправляем запрос к API. Параметры: {ENDPOINT, HEADERS, payload}'
        )
        return homework_statuses.json()
    except Exception:
        raise Exception(
            f'Ошибка во время запроса к API {ENDPOINT}.'
            f' Параметры: {HEADERS, payload}'
        )


def check_response(response):
    """Проверка на пустоту ответа от API."""
    if not isinstance(response, dict):
        raise TypeError('Ответ не является словарем')
    homeworks = response.get('homeworks')
    current_date = response.get('current_date')
    if homeworks is None or current_date is None:
        logging.debug('Отсутствие изменения статуса.')
        raise KeyError('Не найдены нужные ключи')
    if not isinstance(homeworks, list):
        raise TypeError('homeworks в ответе API не является списком.')
    if not isinstance(current_date, int):
        raise TypeError('current_date в ответе API не является int.')
    return homeworks


def parse_status(homework):
    """Сбор данных с API."""
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    if status is None or homework_name is None:
        raise KeyError('Не найдены нужные ключи')
    if not homework_name:
        raise KeyError('Пустое значение по ключу')
    if status not in HOMEWORK_VERDICTS:
        raise KeyError('Не корректный статус домашней работы.')

    verdict = HOMEWORK_VERDICTS.get(status)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

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
