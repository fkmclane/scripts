#!/usr/bin/env python3
import random
import string

morse = {
    'A': '.-',
    'B': '-...',
    'C': '-.-.',
    'D': '-..',
    'E': '.',
    'F': '..-.',
    'G': '--.',
    'H': '....',
    'I': '..',
    'J': '.---',
    'K': '-.-',
    'L': '.-..',
    'M': '--',
    'N': '-.',
    'O': '---',
    'P': '.--.',
    'Q': '--.-',
    'R': '.-.',
    'S': '...',
    'T': '-',
    'U': '..-',
    'V': '...-',
    'W': '.--',
    'X': '-..-',
    'Y': '-.--',
    'Z': '--..',
    '0': '-----',
    '1': '.----',
    '2': '..---',
    '3': '...--',
    '4': '....-',
    '5': '.....',
    '6': '-....',
    '7': '--...',
    '8': '---..',
    '9': '----.',
    ',': '--..--',
    '.': '.-.-.-',
    '?': '..--..',
    ';': '-.-.-.',
    ':': '---...',
    "'": '.----.',
    '-': '-....-',
    '/': '-..-.',
    '(': '-.--.-',
    ')': '-.--.-',
    '_': '..--.-',
}

letters = {code: letter for letter, code in morse.items()}

dot = string.ascii_uppercase
dash = string.digits
separator = '.'
space = '_'
linefeed = '\n'

def encode(message):
    message_code = []

    for line in message.upper().splitlines():
        line_code = []
        for word in line.split(' '):
            word_code = []
            for char in word:
                char_code = []
                if char not in morse:
                    char = '_'
                for bit in morse[char]:
                    char_code.append(random.choice(dot if bit == '.' else dash))
                word_code.append(''.join(char_code))
            line_code.append(separator.join(word_code))
        message_code.append(space.join(line_code))

    message_code.append('')

    return linefeed.join(message_code)

def decode(code):
    message = []

    for line_code in code.upper().split(linefeed):
        if not line_code:
            continue

        line = []
        for word_code in line_code.split(space):
            word = []
            for char_code in word_code.split(separator):
                char = []
                for bit in char_code:
                    char.append('.' if bit in dot else '-')
                word.append(letters[''.join(char)])
            line.append(''.join(word))
        message.append(' '.join(line))

    message.append('')

    return '\n'.join(message)

if __name__ == '__main__':
    import sys

    from argparse import ArgumentParser, FileType

    parser = ArgumentParser(description='encode and decode chase cipher')
    parser.add_argument('-d', action='store_false', default=True, dest='encode', help='decode the message')
    parser.add_argument('infile', nargs='?', default=sys.stdin, type=FileType('r'), help='file to encode or decode (defaults to stdin)')
    parser.add_argument('outfile', nargs='?', default=sys.stdout, type=FileType('w'), help='file to store output (defaults to stdout)')

    args = parser.parse_args()

    function = encode if args.encode else decode

    args.outfile.write(function(args.infile.read()))
