import unittest
from datetime import datetime as dt
from datetime import timedelta as td
from logtime import Log
from logtime import LogItem


class Test(unittest.TestCase):
    def test_split(self):
        d1 = dt(2016, 1, 1, 0, 0)
        d2 = dt(2015, 2, 1, 0, 0)
        m = td(minutes=1)
        log = Log([
            LogItem(d1, d1 + td(minutes=5), []),
            LogItem(d2, d2 + td(minutes=7), []),
        ])
        self.assertEqual(
            list(log._split_by_minute()), [
                LogItem(d1 + 0 * m, d1 + 1 * m, []),
                LogItem(d1 + 1 * m, d1 + 2 * m, []),
                LogItem(d1 + 2 * m, d1 + 3 * m, []),
                LogItem(d1 + 3 * m, d1 + 4 * m, []),
                LogItem(d1 + 4 * m, d1 + 5 * m, []),
                LogItem(d2 + 0 * m, d2 + 1 * m, []),
                LogItem(d2 + 1 * m, d2 + 2 * m, []),
                LogItem(d2 + 2 * m, d2 + 3 * m, []),
                LogItem(d2 + 3 * m, d2 + 4 * m, []),
                LogItem(d2 + 4 * m, d2 + 5 * m, []),
                LogItem(d2 + 5 * m, d2 + 6 * m, []),
                LogItem(d2 + 6 * m, d2 + 7 * m, []),
            ]
        )

    def test_join_two(self):
        d = dt(2016, 1, 1, 0, 0)
        m = td(minutes=5)
        self.assertEqual(
            str_set(Log._join([
                LogItem(d, d + m, ['a']),
                LogItem(d + m, d + 2 * m, ['a'])
            ])), str_set([
                LogItem(d, d + 2 * m, ['a'])
            ])
        )

    def test_dont_join_two(self):
        d = dt(2016, 1, 1, 0, 0)
        m = td(minutes=5)
        self.assertEqual(
            str_set(Log._join([
                LogItem(d, d + m, ['a']),
                LogItem(d + m, d + 2 * m, ['b'])
            ])), str_set([
                LogItem(d, d + m, ['a']),
                LogItem(d + m, d + 2 * m, ['b'])
            ])
        )

    def test_join_three(self):
        d = dt(2016, 1, 1, 0, 0)
        m = td(minutes=5)
        self.assertEqual(
            str_set(Log._join([
                LogItem(d, d + m, ['a']),
                LogItem(d + m, d + 2 * m, ['a']),
                LogItem(d + 2 * m, d + 3 * m, ['a']),
            ])), str_set([
                LogItem(d, d + 3 * m, ['a']),
            ])
        )

    def test_join_two_and_one(self):
        d = dt(2016, 1, 1, 0, 0)
        m = td(minutes=5)
        self.assertEqual(
            str_set(Log._join([
                LogItem(d, d + m, ['a']),
                LogItem(d + m, d + 2 * m, ['a']),
                LogItem(d + 3 * m, d + 4 * m, ['a']),
            ])), str_set([
                LogItem(d, d + 2 * m, ['a']),
                LogItem(d + 3 * m, d + 4 * m, ['a']),
            ])
        )


def str_set(items):
    return set(str(i) for i in items)


if __name__ == '__main__':
    unittest.main()
