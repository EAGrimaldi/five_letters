import json
import logging
import re
import requests as rq
import string
from pathlib import Path
from tqdm import tqdm

BASE_URL = 'https://api.datamuse.com'
WORDS_URL = f'{BASE_URL}/words'
MAX = 1000

def get_json() -> None:
    payloads = [{'sp': f'{letter0}{letter1}???', 'max': f'{MAX}'} for letter0 in string.ascii_lowercase for letter1 in string.ascii_lowercase]

    data = []

    for payload in tqdm(payloads):
        result = rq.get(WORDS_URL, params=payload)
        if len(result.json()) == MAX:
            pl = payload['sp']
            logging.warning(f'get request "sp={pl}" exceeded {MAX} result limit. consider breaking request into sub-requests.')
        data.extend(result.json())

    with open(Path(__file__).parent / 'five_letters.json', 'w') as data_file:
        data_file.write(json.dumps(data, sort_keys=True, indent=4))

def clean_json() -> None:
    with open(Path(__file__).parent / 'five_letters.json', 'r') as data_file:
        data = [element for element in json.load(data_file) if re.match('^[a-z]{5}$', element['word'])]
    # TODO remove all the acronyms and nonsense words
    with open(Path(__file__).parent / 'five_letters_clean.json', 'w') as data_file:
        data_file.write(json.dumps(data, sort_keys=True, indent=4))
            

if __name__ == '__main__':
    get_json()
    clean_json()