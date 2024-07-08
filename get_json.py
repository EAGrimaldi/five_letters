import json
import logging
import operator
import re
import requests as rq
import string
from pathlib import Path
from tqdm import tqdm
from typing import Tuple

BASE_URL = 'https://api.datamuse.com'
WORDS_URL = f'{BASE_URL}/words'
MAX_PER_REQUEST = 1000
MIN_FREQ = 0.03

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
        } for element in json.load(data_file) if re.match('^[a-z]{5}$', element['word'])]

    data.sort(key=operator.itemgetter('freq'), reverse=True)

    with open(Path(__file__).parent / 'five_letters_clean.json', 'w') as data_file:
        data_file.write(json.dumps(data, sort_keys=True, indent=4))

def common_json() -> None:
    with open(Path(__file__).parent / 'five_letters_clean.json', 'r') as data_file:
        data = [element for element in json.load(data_file) if element['freq'] >= MIN_FREQ]

    with open(Path(__file__).parent / 'five_letters_common.json', 'w') as data_file:
        data_file.write(json.dumps(data, sort_keys=True, indent=4))

def lease_common_in_original_wordle(p: bool = False) -> Tuple[str, float]:
    word_2_freq = {}
    least_freq_word = ''
    least_freq_freq = 1000000
    with open(Path(__file__).parent / 'five_letters_clean.json', 'r') as data_file:
        for element in json.load(data_file):
            word_2_freq[element['word']] = element['freq']
    with open(Path(__file__).parent / 'original_wordle_answers.txt', 'r') as data_file:
        for line in data_file:
            word = line.strip()
            if word not in word_2_freq:
                logging.warning(f'missing word: {word}')
                continue
            (least_freq_word, least_freq_freq) = (word, word_2_freq[word]) if word_2_freq[word] < least_freq_freq else (least_freq_word, least_freq_freq)
    if p:
        print(f'least freq word: {least_freq_word}')
        print(f'least freq freq: {least_freq_freq}')
    return (least_freq_word, least_freq_freq)

if __name__ == '__main__':
    clean_json()
    common_json()
