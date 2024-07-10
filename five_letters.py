import argparse
import json
import logging
import math
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import List, Dict

WORD_LENGTH = 5
MAX_GUESSES = 6
MAX_PRINT_TH = 100
GREEN = '\u001b[32m'
YELLOW = '\u001b[33m'
RESET = '\u001b[0m'

def get_args() -> Dict:
    parser = argparse.ArgumentParser('analyze the quality of Wordle guesses')
    parser.add_argument('-pm', '--post-mortem',
        action='store_true',
        help='switch to post mortem mode',
        dest='post-mortem'
    )
    parser.add_argument('-g', '--guesses',
        required=False,
        help=f'comma separated list of guesses',
        dest='guesses'
    )
    parser.add_argument('-a', '--answer',
        required=False,
        help='true answer',
        dest='answer'
    )
    parser.add_argument('-th', '--print-threshold',
        default=0,
        type=int,
        required=False,
        help='print possible answers if fewer than this number remain',
        dest='print-threshold'
    )
    args = vars(parser.parse_args())
    if args['post-mortem']:
        if 'answer' not in args:
            args['answer'] = input('enter the true answer\n')
        assert_valid_guess(args['answer'])
        if 'guesses' not in args:
            args['guesses'] = input(f'enter a comma separated list of guesses\n')
        args['guesses'] = args['guesses'].split(',')
        assert len(args['guesses']) <= MAX_GUESSES, f'invalid number of guesses: {len(args['guesses'])}. number of guesses must be at most {MAX_GUESSES}.'
        for guess in args['guesses']:
            assert_valid_guess(guess)
    return args

def assert_valid_guess(guess) -> None:
    assert re.match('^[a-z]{5}$', guess), f'invalid guess {guess}. valid guesses are strings of exactly {WORD_LENGTH} lowercase letters of the english alphabet.'

class FiveLetters:
    def __init__(self) -> None:
        with open(Path(__file__).parent / 'five_letters_common.json', 'r') as data_file:
            self.data = json.load(data_file)
            logging.warning(f'loaded {len(self.data)} five letter words from Datamuse.\n\tnote: Datamuse contains many names, acronyms, etc that do not qualify as normal words.')
            self.reset_workspace()
        self.final_messages = {
            -1: 'oof...',
            1: 'holy shit!',
            2: 'wowza!',
            3: 'nice!',
            4: 'solid.',
            5: 'not your best work.',
            6: 'close call.',
        }
    def reset_workspace(self) -> None:
        self.workspace = deepcopy(self.data)
    def guess_2_color_string(self, guess: str, answer: str) -> str:
        color_string = ''
        guess_count_dict = Counter()
        answer_count_dict = Counter(answer)
        for i in range(WORD_LENGTH):
            guess_count_dict[guess[i]] += 1
            if guess[i] == answer[i]:
                color_string += 'g'
            elif answer_count_dict[guess[i]] > 0 and guess_count_dict[guess[i]] <= answer_count_dict[guess[i]]:
                color_string += 'y'
            else:
                color_string += 'b'
        return color_string
    def guess_2_pattern(self, guess: str, color_string: str) -> str:
        relevant_count_dict = Counter()
        for i in range(WORD_LENGTH):
            letter, color = guess[i], color_string[i]
            match color:
                case 'g':
                    relevant_count_dict[letter] += 1
                case 'y':
                    relevant_count_dict[letter] += 1
        clauses = []
        for i in range(WORD_LENGTH):
            letter, color = guess[i], color_string[i]
            # reminder: we use `NOT re.match(pattern, word)` to detect VALID words in the dictionary
            # since `A and B and C == not (A or B or C)` we can compose one pattern from an arbitrary collection of simple sub-patterns using or operators
            match color:
                case 'g':
                    clauses.append( '^' + '[a-z]'*i + f'[^{letter}]' + '[a-z]'*(WORD_LENGTH-1-i) + '$' )
                    # will FAIL if the ith letter is _
                    # example: '^[a-z][a-z][^_][a-z][a-z]$'
                case 'y':
                    clauses.append( '^' + '[a-z]'*i + letter + '[a-z]'*(WORD_LENGTH-1-i) + '$' )
                    # will FAIL if the ith letter is NOT _
                    # example: '^[a-z][a-z]_[a-z][a-z]$'
                    if relevant_count_dict[letter] == 1:
                        clauses.append(f'^[^{letter}]{{5}}$')
                        # will FAIL if ANY letter is _
                        # example: '^[^_]{5}$'
                    elif relevant_count_dict[letter] == 2:
                        clauses.append(f'^[^{letter}]*{letter}[^{letter}]*$')
                        # will FAIL if 2 letters are _
                        # (trips are impossible in 5 letter words in english)
                        # example: '^[^_]*_[^_]*$'
                    else:
                        logging.warning('trips? impossible...')
                case 'b':
                    if relevant_count_dict[letter] == 0:
                        clauses.append(f'^[^{letter}]*{letter}[a-z]*$')
                        # will FAIL if NO letters are _
                        # example: '^[^_]*_[a-z]*$'
                    elif relevant_count_dict[letter] == 1:
                        clauses.append(f'^[^{letter}]*{letter}[^{letter}]*{letter}[^{letter}]*$')
                        # will FAIL if 1 letter is _
                        # (trips are impossible in 5 letter words in english)
                        # example: '^[^_]*_[^_]*_[^_]*$'
                    else:
                        logging.warning('trips? impossible...')
        return '|'.join(clauses)
    def apply_guess(self, guess: str, color_string: str) -> float:
        len_old_workspace = len(self.workspace)
        pattern = self.guess_2_pattern(guess, color_string)
        self.workspace = [element for element in self.workspace if not re.match(pattern, element['word'])]
        info_gained = math.log(float(len_old_workspace/float(len(self.workspace))), 2)
        return info_gained
    def apply_color(self, guess: str, color_string: str) -> str:
        guess_with_color = ''
        for i in range(WORD_LENGTH):
            match color_string[i]:
                case 'g':
                    temp = GREEN + guess[i] + RESET
                case 'y':
                    temp = YELLOW + guess[i] + RESET
                case _:
                    temp = guess[i]
            guess_with_color += temp
        return guess_with_color
    def post_mortem(self, guesses: List[str], answer: str, print_threshold: int = 0) -> None:
        # TODO reduce duplicated code
        if print_threshold > MAX_PRINT_TH:
            logging.warning(f'you probably don\'t want to print {print_threshold} words in a python for loop\n\tclamping print_threshold to {MAX_PRINT_TH}.')
        self.reset_workspace()
        total_info_gained = 0
        for guess_number, guess in enumerate(guesses):
            assert_valid_guess(guess)
            color_string = self.guess_2_color_string(guess, answer)
            info_gained = self.apply_guess(guess, color_string)
            total_info_gained += info_gained
            guess_with_color = self.apply_color(guess, color_string)
            print(f'guess {guess_number}: {guess_with_color}')
            print(f'\t{len(self.workspace)} words remaining')
            if 1 < len(self.workspace) <= print_threshold:
                for element in self.workspace:
                    print(f'\t\t{element["word"]}')
            print(f'\t{info_gained} bits of information gained')
            print(f'\t{total_info_gained} total bits of information gained')
        final_message = f'solved in {len(guesses)} - {self.final_messages[len(guesses)]}' if guesses[-1] == answer else self.final_messages[-1]
        print(final_message)
    def live_analysis(self, print_threshold: int = 0) -> None:
        # TODO reduce duplicated code
        if print_threshold > MAX_PRINT_TH:
            logging.warning(f'you probably don\'t want to print {print_threshold} words in a python for loop\n\tclamping print_threshold to {MAX_PRINT_TH}.')
        self.reset_workspace()
        guess_number = 0
        solved = False
        total_info_gained = 0
        while guess_number < MAX_GUESSES and not solved:
            guess, color_string = input('enter a guess and color string, separated by white space\n').split()
            assert_valid_guess(guess)
            assert re.match('^[gyb]{5}$', color_string), f'invalid color string: "{color_string}". valid color strings are strings of exactly {WORD_LENGTH} lowercase letters from the set {"g", "y", "b"}.'
            info_gained = self.apply_guess(guess, color_string)
            total_info_gained += info_gained
            guess_with_color = self.apply_color(guess, color_string)
            print(f'guess {guess_number}: {guess_with_color}')
            print(f'\t{len(self.workspace)} words remaining')
            if 1 < len(self.workspace) <= print_threshold:
                for element in self.workspace:
                    print(f'\t\t{element["word"]}')
            print(f'\t{info_gained} bits of information gained')
            print(f'\t{total_info_gained} total bits of information gained')
            guess_number += 1
            solved = True if color_string == 'ggggg' else False
        final_message = f'solved in {guess_number} - {self.final_messages[guess_number]}' if solved else self.final_messages[-1]
        print(final_message)

if __name__ == '__main__':
    args = get_args()
    fl = FiveLetters()
    if args['post-mortem']:
        fl.post_mortem(guesses=args['guesses'], answer=args['answer'], print_threshold=args['print-threshold'])
    else:
        fl.live_analysis(print_threshold=args['print-threshold'])
