import json
import logging
import operator
import re
import requests as rq
import string
from pathlib import Path
from tqdm import tqdm

BASE_URL = 'https://api.datamuse.com'
WORDS_URL = f'{BASE_URL}/words'
MAX_PER_REQUEST = 1000 #
MIN_FREQ = 0.01

def get_json() -> None:
    payloads = [{'sp': f'{letter0}{letter1}???', 'max': f'{MAX_PER_REQUEST}', 'md': 'f'} for letter0 in string.ascii_lowercase for letter1 in string.ascii_lowercase]

    data = []

    for payload in tqdm(payloads):
        result = rq.get(WORDS_URL, params=payload)
        if len(result.json()) == MAX_PER_REQUEST:
            pl = payload['sp']
            logging.warning(f'get request "sp={pl}" exceeded {MAX_PER_REQUEST} result limit. consider breaking request into sub-requests.')
        data.extend(result.json())

    with open(Path(__file__).parent / 'five_letters.json', 'w') as data_file:
        data_file.write(json.dumps(data, sort_keys=True, indent=4))

def clean_json() -> None:
    with open(Path(__file__).parent / 'five_letters.json', 'r') as data_file:
        data = [{
            'word': element['word'],
            'freq': float(element['tags'][0][2:])
        } for element in json.load(data_file) if is_reasonable_word(element)]
        data.sort(key=operator.itemgetter('freq'))
    
    with open(Path(__file__).parent / 'five_letters_clean.json', 'w') as data_file:
        data_file.write(json.dumps(data, sort_keys=True, indent=4))

def is_reasonable_word(word_dict: dict) -> bool:
    if not re.match('^[a-z]{5}$', word_dict['word']):
        return False
    if float(word_dict['tags'][0][2:]) < MIN_FREQ:
        return False
    return True

if __name__ == '__main__':
    clean_json()
