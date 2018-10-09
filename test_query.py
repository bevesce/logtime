from __future__ import unicode_literals

import unittest
from datetime import datetime

from logtime.query import Lexer, parse, Token
from logtime.logtime import LogItem, Log



class TestLexer(unittest.TestCase):
    def tokens(self, text):
        self.tokens = Lexer().tokenize(text)
        return self

    def are(self, tokens):
        self.assertEqual(
            self.tokens,
            [Token(t, v) for t, v in tokens]
        )

    def test_words(self):
        self.tokens('a b c').are((('search term', 'a b c'), ))

    def test_boolean_attribute(self):
        self.tokens('and').are((('boolean operator', 'and'), ))

    def test_slice(self):
        self.tokens('[today;tomorrow]').are((('slice', ('today', 'tomorrow')), ))

    def test_start_slice(self):
        self.tokens('[today;]').are((('slice', ('today', None)), ))

    def test_end_slice(self):
        self.tokens('[;]').are((('slice', (None, None)), ))

    def test_full_slice(self):
        self.tokens('[;tomorrow]').are((('slice', (None, 'tomorrow')), ))

    def test_01(self):
        self.tokens('w and x or y [today;tomorrow]').are((
            ('search term', 'w'),
            ('boolean operator', 'and'),
            ('search term', 'x'),
            ('boolean operator', 'or'),
            ('search term', 'y'),
            ('slice', ('today', 'tomorrow')),
        ))



class TestParser(unittest.TestCase):
    def query(self, text):
        self.query = parse(text)
        return self

    def shows_as(self, text):
        self.assertEqual(str(self.query), text)

    def test_word(self):
        self.query('word').shows_as('(word [;])')

    def test_boolean(self):
        self.query('foo and bar').shows_as('((foo and bar) [;])')

    def test_parens_1(self):
        self.query('foo and bar or qux').shows_as('(((foo and bar) or qux) [;])')

    def test_parens_2(self):
        self.query('foo and (bar or qux)').shows_as('((foo and (bar or qux)) [;])')

    def test_not_1(self):
        self.query('not x').shows_as('((not x) [;])')

    def test_not_2(self):
        self.query('not (x or w)').shows_as('((not (x or w)) [;])')

    def test_not_3(self):
        self.query('x and not y').shows_as('((x and (not y)) [;])')

    def test_slice_1(self):
        self.query('x [2016-10-10;2016-10-10]').shows_as(
            '(x [2016-10-10 00:00:00;2016-10-10 00:00:00])'
        )

    def test_slice_2(self):
        self.query('x [2016-10-10;]').shows_as(
            '(x [2016-10-10 00:00:00;])'
        )

    def test_slice_3(self):
        self.query('x [;2016-10-10]').shows_as(
            '(x [;2016-10-10 00:00:00])'
        )

    def test_slice_4(self):
        self.query('x [;]').shows_as(
            '(x [;])'
        )

    def test_slice_5(self):
        self.query('[2016-10-10;2016-10-11]').shows_as(
            '( [2016-10-10 00:00:00;2016-10-11 00:00:00])'
        )

    def test_01(self):
        self.query(
            'w or not x and (r or u)'
        ).shows_as(
            '((w or (not (x and (r or u)))) [;])'
        )


class TestQuery(unittest.TestCase):
    def quering(self, logitems):
        self.logitems = Log([self.make_logitem(l) for l in logitems])
        return self

    def by(self, text):
        self.logitems = list(parse(text).filter(self.logitems))
        return self

    def gives(self, logitems):
        self.assertEqual(
            self.logitems,
            [self.make_logitem(l) for l in logitems]
        )

    def make_logitem(self, l):
        s, e, t = l
        return LogItem(datetime(*s), datetime(*e), t.split('/'))

    def test_word(self):
        self.quering([
            ((2016, 10, 11), (2016, 10, 11), 'w'),
            ((2016, 10, 11), (2016, 10, 11), 'e'),
        ]).by('w').gives([
            ((2016, 10, 11), (2016, 10, 11), 'w'),
        ])

    def test_and(self):
        self.quering([
            ((2016, 10, 11), (2016, 10, 11), 'e/r'),
            ((2016, 10, 11), (2016, 10, 11), 'w/r'),
            ((2016, 10, 11), (2016, 10, 11), 'w/e'),
        ]).by('w and r').gives([
            ((2016, 10, 11), (2016, 10, 11), 'w/r'),
        ])

    def test_or(self):
        self.quering([
            ((2016, 10, 11), (2016, 10, 11), 'e/r'),
            ((2016, 10, 11), (2016, 10, 11), 'q/e'),
            ((2016, 10, 11), (2016, 10, 11), 'w/r'),
            ((2016, 10, 11), (2016, 10, 11), 'w/q'),
        ]).by('w or r').gives([
            ((2016, 10, 11), (2016, 10, 11), 'e/r'),
            ((2016, 10, 11), (2016, 10, 11), 'w/r'),
            ((2016, 10, 11), (2016, 10, 11), 'w/q'),
        ])

    def test_not(self):
        self.quering([
            ((2016, 10, 11), (2016, 10, 11), 'r'),
            ((2016, 10, 11), (2016, 10, 11), 'w'),
        ]).by('not w').gives([
            ((2016, 10, 11), (2016, 10, 11), 'r'),
        ])

    def test_slice(self):
        self.quering([
            ((2016, 9, 1), (2016, 9, 1), 'r'),
            ((2016, 10, 5), (2016, 10, 5), 'r'),
            ((2016, 11, 5), (2016, 11, 5), 'r'),
        ]).by('[2016-10-01;2016-10-10]').gives([
            ((2016, 10, 5), (2016, 10, 5), 'r'),
        ])

    def test_slice2(self):
        self.quering([
            ((2016, 9, 1), (2016, 9, 10), 'r'),
        ]).by('[2016-09-04;2016-09-6]').gives([
            ((2016, 9, 4), (2016, 9, 6), 'r'),
        ])

    def test_slice(self):
        log = Log("""2018-05-30 16:50
living / holidays / barcelona
2018-06-04 11:20""")
        output = log.filter('living [2018-05-31;2018-06-01]')
        self.assertEqual(str(output), """2018-05-31 00:00
living / holidays / barcelona
2018-06-01 00:00""")

    def test_bug_001(self):
        log = Log("""2018-10-04 11:55
living / hanging
2018-10-04 13:10
a3m / no-rm""")
        output = log.filter('a3m')
        print('output', output)
        self.assertEqual(str(output), """2018-10-04 13:10
a3m / no-rm""")


if __name__ == '__main__':
    unittest.main()
