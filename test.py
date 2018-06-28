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

    def test_slicing_with_start(self):
        log = Log("""
2018-06-28 09:00
test
2018-06-28 10:00
test2
2018-06-29 10:00
""")
        output = str(log['2018-06-28':])
        self.assertEqual(output, """2018-06-28 09:00
test
2018-06-28 10:00
test2
2018-06-29 10:00""")

    def test_slicing_with_end(self):
        log = Log("""
2018-06-28 09:00
test
2018-06-28 10:00
test2
2018-06-29 10:00
""")
        output = str(log[:'2018-06-29'])
        self.assertEqual(output, """2018-06-28 09:00
test
2018-06-28 10:00
test2
2018-06-29 00:00""")

    def test_slicing_with_start_and_end(self):
        log = Log("""
2018-06-28 09:00
test
2018-06-28 10:00
test2
2018-06-29 10:00
""")
        output = str(log['2018-06-28 12:00':'2018-06-29'])
        self.assertEqual(output, """2018-06-28 12:00
test2
2018-06-29 00:00""")

    def test_slicing_with_start_end_and_step(self):
        log = Log("""
2018-06-27 09:00
test0
2018-06-28 09:00
test1
2018-06-28 10:00
test2
2018-06-29 10:00
""")
        output = log['2018-06-27':'2018-06-29':td(hours=24)]
        self.assertEqual(str(output[0]), """2018-06-27 09:00
test0
2018-06-28 00:00""")
        self.assertEqual(str(output[1]), """2018-06-28 00:00
test0
2018-06-28 09:00
test1
2018-06-28 10:00
test2
2018-06-29 00:00""")

    def test_slicing_with_start_and_step(self):
        log = Log("""
2018-06-27 09:00
test0
2018-06-28 09:00
test1
2018-06-28 10:00
test2
2018-06-29 10:00
""")
        output = log['2018-06-27'::td(hours=24)]
        self.assertEqual(str(output[0]), """2018-06-27 09:00
test0
2018-06-28 00:00""")
        self.assertEqual(str(output[1]), """2018-06-28 00:00
test0
2018-06-28 09:00
test1
2018-06-28 10:00
test2
2018-06-29 00:00""")
        self.assertEqual(str(output[2]), """2018-06-29 00:00
test2
2018-06-29 10:00""")

    def test_slicing_with_step_function(self):
        log = Log("""
2018-01-27 09:00
test
2018-03-29 10:00
""")
        output = log[::lambda start: next_month(start)]
        self.assertEqual(str(output[0]), """2018-01-27 09:00
test
2018-02-01 00:00""")
        self.assertEqual(str(output[1]), """2018-02-01 00:00
test
2018-03-01 00:00""")
        self.assertEqual(str(output[2]), """2018-03-01 00:00
test
2018-03-29 10:00""")



def next_month(start):
    return (start + td(days=32)).replace(day=1, hour=0, minute=0, second=0)

if __name__ == '__main__':
    unittest.main()
