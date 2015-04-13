"""
Log and show time spent on tasks.
Using without argument will show logged tasks with time spent on them.
Using with some text will start new task.

Usage:
    logtime.py <task_description>...
    logtime.py -e
    logtime.py -f
    logtime.py

Options:
    -h --help                     Show this screen.
    -e --end                      End current task.
    -f --file                     Open file with log.
"""

from datetime import datetime, timedelta
from collections import defaultdict
import bisect
import docopt
import subprocess
from config import logtime_path

import colors


DATETIME_FORMAT = '%Y-%m-%d %H:%M'
COMMENT_INDICATOR = '#'


def separate_timedelta(delta):
    ZERO_TIME = timedelta()
    H24 = timedelta(hours=24)
    minus = False
    if delta < ZERO_TIME:
        # timedelta(hours=8) - timedelta(hours=9) = -1 day, 23:00:00
        # so it need to be flipped to 1 hour
        delta = H24 - delta
        minus = True
    hours = delta.seconds / 3600
    minutes = (delta.seconds % 3600) / 60
    return hours, minutes, minus


def format_timedelta(delta):
    hours, minutes, minus = separate_timedelta(delta)
    if minus:
        return '-{}:{:02d}'.format(hours, minutes)
    else:
        return '{}:{:02d}'.format(hours, minutes)


def format_timedelta_for_redmine(delta):
    hours, minutes, minus = separate_timedelta(delta)
    minutes = '{:.3f}'.format(minutes / 60.)
    return '{}.{}'.format(hours, minutes[2:])


class Parser(object):
    def __init__(self, text):
        self.text = text.strip()

    def parse(self):
        for start, title, end in self._parse_to_raw():
            yield LogItem(title, start=start, end=end)

    def _parse_to_raw(self):
        prev_date = None
        prev_title = None
        for date, title in self._parse_lines():
            if date:
                if prev_title:
                    yield (prev_date, prev_title, date)
                    prev_title = None
                prev_date = date
            elif title:
                prev_title = title
        if prev_title:
            yield (prev_date, prev_title, None)

    def _parse_lines(self):
        lines = self.text.splitlines()
        for line in lines:
            if line.startswith(COMMENT_INDICATOR):
                print line
                continue
            yield self._parse_line(line)

    def _parse_line(self, line):
        try:
            date = datetime.strptime(line, DATETIME_FORMAT)
            title = None
        except ValueError:
            date = None
            title = line
        return date, title


class LogItem(object):
    DEFAULT_START_DATE = datetime(1900, 01, 01, 00, 00)
    BREAK_INDICATOR = '@'

    def __init__(self, title, start, end):
        self.title = title
        self.start = start or self.DEFAULT_START_DATE
        self.end = end or datetime.now()

    @property
    def duration(self):
        return self.end - self.start

    @property
    def is_break(self):
        return self.title.startswith(self.BREAK_INDICATOR)

    @property
    def year(self):
        return self.start.year

    @property
    def month(self):
        return (self.start.year, self.start.month)

    @property
    def week(self):
        return (self.start.year, self.start.isocalendar()[1])

    @property
    def day(self):
        return (self.start.year, self.start.month, self.start.day)

    def __repr__(self):
        return 'LogItem("{}", start={}, end={})'.format(
            self.title, repr(self.start), repr(self.end)
        )


class SomeTime(object):
    def __init__(self):
        self.duration = timedelta()
        self.break_duration = timedelta()
        if self.subtime_class:
            self.subtimes = defaultdict(self.subtime_class)
        self.keys = []

    def add(self, logitem):
        self._add_duration(logitem)
        bisect.insort_left(self.keys, self.subtime_key(logitem))
        self.subtimes[self.subtime_key(logitem)].add(logitem)

    def _add_duration(self, logitem):
        if logitem.is_break:
            self.break_duration += logitem.duration
        else:
            self.duration += logitem.duration

    def newest_subtime(self):
        return self.subtimes[self.keys[-1]]


class Task(SomeTime):
    subtime_class = None

    def __init__(self):
        self.logitems = []
        self.title = None
        self.duration = timedelta()

    def add(self, logitem):
        self.title = logitem.title
        self.logitems.append(logitem)
        self.duration += logitem.duration

    @property
    def is_break(self):
        return self.title.startswith(LogItem.BREAK_INDICATOR)


class Day(SomeTime):
    subtime_class = Task

    def subtime_key(self, logitem):
        return logitem.title

    def iter_tasks(self):
        for k in self.keys:
            yield self.subtimes[k]


class Week(SomeTime):
    subtime_class = Day

    def subtime_key(self, logitem):
        return logitem.day

    def newest_day(self):
        return self.newest_subtime()


class Month(SomeTime):
    subtime_class = Week

    def subtime_key(self, logitem):
        return logitem.week

    def newest_week(self):
        return self.newest_subtime()


class Year(SomeTime):
    subtime_class = Month

    def subtime_key(self, logitem):
        return logitem.month

    def newest_month(self):
        return self.newest_subtime()


class Calendar(SomeTime):
    subtime_class = Year

    @classmethod
    def from_file(cls, path):
        return Calendar(Parser(open(logtime_path).read()).parse())

    def __init__(self, logitems):
        super(Calendar, self).__init__()
        self.years = defaultdict(self.subtime_class)
        for logitem in logitems:
            self.add(logitem)
        self.keys.sort()

    def subtime_key(self, logitem):
        return logitem.year

    def newest_year(self):
        return self.newest_subtime()


class Printer(object):
    def today_summary(self, calendar):
        print ''
        year = calendar.newest_year()
        self._today_summary_year(year)
        month = year.newest_month()
        self._today_summary_month(month)
        week = month.newest_week()
        self._today_summary_week(week)
        day = week.newest_day()
        print ''
        self._today_summary_day(day)
        print ''
        self._today_summary_tasks(day)

    def _today_summary_year(self, year):
        pass

    def _today_summary_month(self, month):
        print 'month:', format_timedelta(month.duration)

    def _today_summary_week(self, week):
        print 'week: ', format_timedelta(week.duration)

    def _today_summary_day(self, day):
        print 'today: {} {}= {} - {}{}'.format(
            format_timedelta(day.duration),
            colors.GRAY,
            format_timedelta(day.duration + day.break_duration),
            format_timedelta(day.break_duration),
            colors.DEFC,
        )

    def _today_summary_tasks(self, day):
        for task in day.iter_tasks():
            if task.is_break:
                print colors.gray('{} {} {}'.format(
                    format_timedelta(task.duration),
                    format_timedelta_for_redmine(task.duration),
                    task.title
                ))
            else:
                print '{} {} {}'.format(
                    format_timedelta(task.duration),
                    colors.gray(format_timedelta_for_redmine(task.duration)),
                    task.title
                )


def start_task(title):
    new_line = make_timestamp() + '\n' + ' '.join(title)
    append_line(new_line)


def end_task():
    new_line = make_timestamp()
    append_line(new_line)


def make_timestamp():
    return datetime.now().strftime(DATETIME_FORMAT)


def append_line(line):
    old = open(logtime_path).read()
    if not old.endswith('\n'):
        line = '\n' + line
    open(logtime_path, 'a').write(line)


if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)
    if arguments['<task_description>']:
        start_task(arguments['<task_description>'])
    if arguments['--end']:
        end_task()
    if arguments['--file']:
        subprocess.call(['subl', logtime_path])
    Printer().today_summary(
        Calendar.from_file(logtime_path)
    )
