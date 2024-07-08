import json
import logging
import math
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import List

WORD_LENGTH = 5
MAX_GUESSES = 6
WS_PRINT_MAX = 100

class FiveLetters:
    def __init__(self) -> None:
        with open(Path(__file__).parent / 'five_letters_clean.json', 'r') as data_file:
            self.data = json.load(data_file)
            logging.warning(f'loaded {len(self.data)} five letter words from Datamuse. note: Datamuse contains many common acronyms that do not qualify as normal words.')
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
        self.error_messages = {
            'invalid guess': f'invalid guess. valid guesses are strings of exactly {WORD_LENGTH} lowercase letters of the english alphabet.',
            'invalid color string': f'invalid color string. valid color strings are strings of exactly {WORD_LENGTH} lowercase letters from the set {"g", "y", "b"}.',
        }
    def reset_workspace(self) -> None:
        self.workspace = deepcopy(self.data)
    def valid_guess(self, guess: str) -> bool:
        return True if re.match('^[a-z]{5}$', guess) else False
    def valid_color_string(self, color_string: str) -> bool:
        return True if re.match('^[gyb]{5}$', color_string) else False
    def guess_2_color_string(self, guess: str, answer: str) -> str:
        assert self.valid_guess(guess), self.error_messages['invalid guess']
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
    def guess_2_pattern(self, guess: str, color_string: str = 'bbbbb') -> str:
        assert self.valid_guess(guess), self.error_messages['invalid guess']
        assert self.valid_color_string(color_string), self.error_messages['invalid color string']
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
            match color:
                case 'g':
                    clauses.append( '^' + '[a-z]'*i + f'[^{letter}]' + '[a-z]'*(WORD_LENGTH-1-i) + '$' )
                    # will FAIL if the ith letter is _
                    # example: '^[a-z][a-z][^x][a-z][a-z]$'
                case 'y':
                    clauses.append( '^' + '[a-z]'*i + letter + '[a-z]'*(WORD_LENGTH-1-i) + '$' )
                    # will FAIL if the ith letter is NOT _
                    # example: '^[a-z][a-z]x[a-z][a-z]$'
                    if relevant_count_dict[letter] == 1:
                        clauses.append(f'^[^{letter}]{{5}}$')
                        # will FAIL if ANY letter is _
                        # example: '^[^x]{5}$'
                    elif relevant_count_dict[letter] == 2:
                        clauses.append(f'^[^{letter}]*{letter}[^{letter}]*$')
                        # will FAIL if 2 letters are _
                        # example: '^[^x]*x[^x]*$'
                        # TODO find a better way to handle double letter words
                    else:
                        logging.warning('trips? impossible...')
                case 'b':
                    if relevant_count_dict[letter] == 0:
                        clauses.append(f'{letter}')
                        # will FAIL if NO letters are _
                        # example: 'x'
                    elif relevant_count_dict[letter] == 1:
                        clauses.append(f'{letter}[^{letter}]*{letter}')
                        # will FAIL if 1 letter is _
                        # example: 'x[^x]*x'
                        # TODO find a better way to handle double letter words
                    else:
                        logging.warning('trips? impossible...')
        return '|'.join(clauses)
    def apply_guess(self, guess: str, color_string: str = 'bbbbb') -> float:
        assert self.valid_guess(guess), self.error_messages['invalid guess']
        assert self.valid_color_string(color_string), self.error_messages['invalid color string']
        len_old_workspace = len(self.workspace)
        pattern = self.guess_2_pattern(guess, color_string)
        self.workspace = [element for element in self.workspace if not re.match(pattern, element['word'])]
        info_gained = math.log(float(len_old_workspace/float(len(self.workspace))), 2)
        return info_gained
    def post_mortem(self, guesses: List[str], answer: str, ws_print_condition: int = 0) -> None:
        # TODO reduce duplicated code
        if ws_print_condition > WS_PRINT_MAX:
            logging.warning(f'you probably don\'t want to print {ws_print_condition} words in a python for loop\nclamping ws_print_condition to {WS_PRINT_MAX}.')
        self.reset_workspace()
        total_info_gained = 0
        for guess in guesses:
            color_string = self.guess_2_color_string(guess, answer)
            info_gained = self.apply_guess(guess, color_string)
            total_info_gained += info_gained
            print(f'guessed {guess}, giving {color_string}')
            if len(self.workspace) <= ws_print_condition:
                for element in self.workspace:
                    print(f'\t\t{element["word"]}')
            print(f'\t{len(self.workspace)} words remaining')
            print(f'\t{info_gained} bits of information gained')
            print(f'\t{total_info_gained} total bits of information gained')
        final_message = f'solved in {len(guesses)} - {self.final_messages[len(guesses)]}' if guesses[-1] == answer else self.final_messages[-1]
        print(final_message)
    def live_analysis(self, ws_print_condition: int = 0) -> None:
        # TODO reduce duplicated code
        if ws_print_condition > WS_PRINT_MAX:
            logging.warning(f'you probably don\'t want to print {ws_print_condition} words in a python for loop\nclamping ws_print_condition to {WS_PRINT_MAX}.')
        self.reset_workspace()
        num_guesses = 0
        solved = False
        total_info_gained = 0
        while num_guesses < MAX_GUESSES and not solved:
            guess, color_string = input('enter a guess and color string, separated by white space\n').split()
            info_gained = self.apply_guess(guess, color_string)
            total_info_gained += info_gained
            print(f'guessed {guess}, giving {color_string}')
            if len(self.workspace) <= ws_print_condition:
                for element in self.workspace:
                    print(f'\t\t{element["word"]}')
            print(f'\t{len(self.workspace)} words remaining')
            print(f'\t{info_gained} bits of information gained')
            print(f'\t{total_info_gained} total bits of information gained')
            num_guesses += 1
            solved = True if color_string == 'ggggg' else False
        final_message = f'solved in {num_guesses} - {self.final_messages[num_guesses]}' if solved else self.final_messages[-1]
        print(final_message)

if __name__ == '__main__':
    fl = FiveLetters()
    fl.live_analysis(ws_print_condition=100)
