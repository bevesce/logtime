import unittest
from datetime import datetime as dt
from datetime import timedelta as td
from logtime.logtime import Log
from logtime.logtime import LogItem
from logtime.query import parse


class CutDate(unittest.TestCase):
    def test_01(self):
        l = LogItem(
            dt(2016, 10, 1), dt(2016, 10, 1), []
        ).cut_to_dates(dt(2015, 1, 1), dt(2017, 1, 1))
        self.assertEqual(
            l,
            LogItem(
                dt(2016, 10, 1), dt(2016, 10, 1), []
            )
        )

    def test_02(self):
        l = LogItem(
            dt(2016, 10, 1), dt(2016, 10, 1), []
        ).cut_to_dates(dt(2017, 1, 1), dt(2017, 1, 1))
        self.assertEqual(
            l, None
        )

    def test_03(self):
        l = LogItem(
            dt(2016, 10, 1), dt(2016, 10, 1), []
        ).cut_to_dates(dt(2015, 1, 1), dt(2015, 1, 1))
        self.assertEqual(
            l, None
        )

    def test_04(self):
        l = LogItem(
            dt(2016, 10, 1), dt(2016, 10, 10), []
        ).cut_to_dates(dt(2015, 1, 1), dt(2016, 10, 5))
        self.assertEqual(
            l,
            LogItem(
                dt(2016, 10, 1), dt(2016, 10, 5), []
            )
        )

    def test_05(self):
        l = LogItem(
            dt(2016, 10, 1), dt(2016, 10, 10), []
        ).cut_to_dates(dt(2016, 10, 5), dt(2017, 1, 1))
        self.assertEqual(
            l,
            LogItem(
                dt(2016, 10, 5), dt(2016, 10, 10), []
            )
        )

    def test_06(self):
        l = LogItem(
            dt(2016, 10, 1), dt(2016, 10, 10), []
        ).cut_to_dates(dt(2016, 10, 2), dt(2016, 10, 8))
        self.assertEqual(
            l,
            LogItem(
                dt(2016, 10, 2), dt(2016, 10, 8), []
            )
        )


log = Log("""2016-09-26 14:00
tv / steven universe
2016-09-26 15:00
eating / spiders
2016-09-26 15:15
programming / logtime / readme
2016-09-26 17:45
programming / finanse
2016-09-26 19:00""")

print('\n\n')

print(log.filter('[2016-09-26 15:30;]'))
print('\n\n')
print(print(log.group(0)))
print('\n\n')

print(log.sum())
print('\n\n')

print(log.filter('programming or tv[2016-09-26 14:30;2016-09-26 15:30]'))


if __name__ == '__main__':
    unittest.main()
