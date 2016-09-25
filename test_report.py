from logtime.logtime import Log
from logtime.logtime import LogItem
from logtime.query import parse
from logtime import report
from datetime import timedelta
from datetime import datetime


log = Log("""
2016-09-25 20:00
1
2016-09-25 21:30
2 - a
2016-09-25 21:45
2 - a - x
2016-09-25 22:00
2 - a - y
2016-09-25 22:14
2 - b
2016-09-25 22:45
""")

print('# progress')
report.print_progress(log, timedelta(hours=2))
print('')
print('# breakdown')
report.print_breakdown(log)
print('')
print('# timeline')
report.print_timeline(
    log,
    datetime(2016, 9, 25, 16),
    datetime(2016, 9, 25, 23, 59), timedelta(minutes=30)
)
print('')

