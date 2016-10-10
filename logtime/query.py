import re
from datetime import datetime
from collections import namedtuple

from .parse_date import parse_date
from .logtime import Log


Token = namedtuple('Token', ['type', 'value'])


def parse(text):
    return Parser().parse(text)


WHITE_SPACE = (' ', '\n', '\t')
PARENTHESIS = ('(', ')')
SLICE_START = '['
SLICE_SEPARATOR = ';'
SLICE_END = ']'
WORD_BREAKS = WHITE_SPACE + (SLICE_START, None) + PARENTHESIS
BOOLEAN_OPERATORS = ('and', 'not', 'or')
PRECEDENCE = {
    'or': 10,
    'and': 11,
    'not': 12,
    '//': 20,
    '/': 20,
}


class Lexer:
    def tokenize(self, text):
        self.tokens = []
        self.chars = list(text)
        while self.chars:
            c = self.pick()
            if c in WHITE_SPACE:
                self.pop()
            elif c in PARENTHESIS:
                self.add('parenthesis', self.pop())
            elif c == '"':
                self.read_words_until_quote()
            elif c == SLICE_START:
                self.read_slice()
            else:
                self.read_word()
        return list(self.clean_up(self.tokens))

    def pick(self):
        if self.chars:
            return self.chars[0]

    def pop(self):
        if self.chars:
            return self.chars.pop(0)

    def read_words_until_quote(self):
        self.pop()
        word = ''
        while c.pick() and c.pick() != '"':
            word += self.pop()
        self.add('search term', word)

    def read_word(self):
        word = self.read_until_word_break()
        if word in BOOLEAN_OPERATORS:
            self.add('boolean operator', word)
        else:
            self.add('search term', word)

    def read_until_word_break(self):
        word = ''
        while self.pick() not in WORD_BREAKS:
            word += self.pop()
        return word

    def read_slice(self):
        self.pop()
        start = ''
        while self.pick() and self.pick() != SLICE_SEPARATOR:
            start += self.pop()
        self.pop()
        stop = ''
        while self.pick() and self.pick() != SLICE_END:
            stop += self.pop()
        self.add('slice', (start or None, stop or None))
        self.pop()

    def add(self, type, value):
        self.tokens.append(Token(type, value))

    def clean_up(self, tokens):
        return self.join_search_terms(tokens)

    def join_search_terms(self, tokens):
        previous = None
        for token in tokens:
            if previous and previous.type == 'search term' and token.type == 'search term':
                previous = Token('search term', previous.value + ' ' + token.value)
            else:
                if previous:
                    yield previous
                previous = token
        if previous:
            yield previous


class Parser:
    def parse(self, text):
        self.text = text
        self.tokens = Lexer().tokenize(text)
        query = self.parse_slice()
        return query

    def pick(self):
        if self.tokens:
            return self.tokens[0]
        return None

    def pop(self):
        if self.tokens:
            return self.tokens.pop(0)
        return None

    def parse_slice(self):
        if self.pick().type != 'slice':
            left = self.parse_boolean_expression(None, 0)
        else:
            left = None
        slice_token = self.pop()
        if slice_token and slice_token.type == 'slice':
            start, end = slice_token.value
        else:
            start, end = None, None
        return Slice(left, start, end)

    def parse_boolean_expression(self, left, precedence):
        t = self.pick()
        if t and not left:
            left = self.parse_unary_boolean_expression()
        t = self.pick()
        if t and t.type == 'boolean operator':
            current_precedence = PRECEDENCE[t.value]
            if current_precedence > precedence:
                self.pop()
                right = self.parse_boolean_expression(
                    self.parse_unary_boolean_expression(), current_precedence
                )
                return self.parse_boolean_expression(
                    BooleanExpression(left, t.value, right), precedence
                )
        return left

    def parse_unary_boolean_expression(self):
        t = self.pick()
        if t.type == 'parenthesis' and t.value == '(':
            return self.parse_parenthesis()
        if t.type == 'boolean operator' and t.value == 'not':
            self.pop()
            return UnaryBooleanExpression('not', self.parse_boolean_expression(None, 0))
        return Atom(*self.pop())

    def parse_parenthesis(self):
        self.pop()
        expression = self.parse_boolean_expression(None, 0)
        self.pop()
        return expression


class Query:
    pass


class Slice(Query):
    def __init__(self, left, start, stop):
        self.left = left
        self.start = parse_date(start) if start is not None else None
        self.stop = parse_date(stop) if stop is not None else None

    def __str__(self):
        return '({} [{};{}])'.format(
            self.left or '', self.start or '', self.stop or ''
        )

    def filter(self, log):
        if self.left:
            return Log(
                l for l in log if self.left.matches(l)
            )[self.start:self.stop]
        return log[self.start:self.stop]

    def matches(self, logitem):
        left_side = True
        if self.left:
            left_side = self.left.matches(logitem)
        if self.start and logitem.end < self.start:
            return False
        if self.stop and logitem.start > self.stop:
            return False
        return left_side


class BooleanExpression(Query):
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

    def __str__(self):
        return '({} {} {})'.format(self.left, self.operator, self.right)

    def matches(self, logitem):
        left_side = self.left.matches(logitem)
        right_side = self.right.matches(logitem)
        if self.operator == 'and':
            return left_side and right_side
        elif self.operator == 'or':
            return left_side or right_side


class UnaryBooleanExpression(Query):
    def __init__(self, operator, right):
        self.operator = operator
        self.right = right

    def __str__(self):
        return '({} {})'.format(self.operator, self.right)

    def matches(self, logitem):
        return not self.right.matches(logitem)


class Atom(Query):
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def __str__(self):
        return '{}'.format(self.value)

    def matches(self, logitem):
        return self.value in logitem.tags
