"""Home work's Checker TeleBot.
Copyright (C) 2022 Authors: Dmitry Korepanov, Yandex practikum
License Free
Version: 1.0.3 2022
"""

import datetime
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from typing import Dict

from exceptions import (
    EmptyResponseFromAPIError, EndpointError,
    TelegramError, WrongResponseCodeError,
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD: float = 600
ENDPOINT = os.getenv('ENDPOINT')
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS: Dict[str, str] = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

REQUEST_TIMEOUT_SEC: float = 0.5


def check_tokens() -> bool:
    """Проверяет наличие TOKENS."""
    logging.info('Проверка наличия всех токенов')
    return all([PRACTICUM_TOKEN,
                TELEGRAM_TOKEN,
                TELEGRAM_CHAT_ID])


def send_message(bot: telegram.bot.Bot, message: str) -> None:
    """Отправляет сообщение в telegram."""
    try:
        logging.info('Начало отправки статуса в telegram')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Статус отправлен в telegram.')
    except telegram.error.TelegramError as error:
        logging.error(f'Сообщение в Telegram не отправлено: {error}')
        raise TelegramError(f'Ошибка отправки статуса в telegram: {error}')


def get_api_answer(timestamp: int) -> dict:
    """Отправляет запрос к API и получает список домашних работ."""
    timestamp = timestamp or int(time.time())
    params_request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    message = (f'Начало запроса к API. Запрос: '
               f'{params_request["url"]}, '
               f'{params_request["headers"]}, '
               f'{params_request["params"]}.'
               )
    logging.info(message)
    try:
        response = requests.get(**params_request,
                                timeout=REQUEST_TIMEOUT_SEC)
        if response.status_code != HTTPStatus.OK:
            logging.error(
                f'API Endpoint {params_request["url"]} c параметрами '
                f'{params_request["params"]} не возвращает status code 200. '
                f'Код ответа: {response.status_code}.'
            )
            raise WrongResponseCodeError(
                f'Ответ API не возвращает status code 200. '
                f'Код ответа: {response.status_code}. '
                f'Причина: {response.reason}. '
                f'Описание: {response.text}.'
            )
        return response.json()
    except Exception as error:
        logging.error(
            f'Проблема при обращении к {params_request["url"]}. '
            f'Ошибка {error}.', exc_info=True
        )
        raise EndpointError(
            f'Проблема при обращении к {params_request["url"]}. '
            f'Ошибка {error}.'
        )


def check_response(response: dict) -> list:
    """Проверяет ответ API на корректность."""
    logging.info('Проверка ответа API на корректность')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является dict')
    if 'homeworks' not in response or 'current_date' not in response:
        raise EmptyResponseFromAPIError('Нет ключа homeworks в ответе API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('homeworks не является list')
    return homeworks


def parse_status(homework: dict) -> str:
    """Извлекает из информации о домашней работе статус этой работы."""
    logging.info('Проводим проверки и извлекаем статус работы')
    if 'homework_name' not in homework:
        raise KeyError('Нет ключа homework_name в ответе API')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Недокументированный статус работы '
                         f'{homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствует TOKEN. Бот остановлен!'
        logging.critical(message)
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    now = datetime.datetime.now()
    start_message = 'Бот начал свою работу'
    send_message(
        bot,
        f'Бот начал свою работу: {now.strftime("%d-%m-%Y %H:%M")}')
    logging.debug(start_message)
    prev_message: str = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get(
                'current_date', timestamp
            )
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
            else:
                message = 'Нет новых статусов'
            if message != prev_message:
                send_message(bot, message)
                prev_message = message
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.FileHandler(
                os.path.abspath('program.log'), mode='a', encoding='UTF-8'),
            logging.StreamHandler(stream=sys.stdout)],
        format='%(asctime)s, %(levelname)s, %(message)s,'
               '%(name)s, %(message)s,', datefmt='%d-%m-%Y %H-%M',
    )
    try:
        main()
    except logging.error('Бот завершил свою работу.'):
        sys.exit()
