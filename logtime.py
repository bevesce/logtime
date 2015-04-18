#!/usr/bin/env python
"""
Log and show time spent on tasks.
Using without argument will show logged tasks with time spent on them.
Using with some text will start new task.

Usage:
    logtime.py
    logtime.py <task_description>...
    logtime.py -e
    logtime.py -f
    logtime.py -s

Options:
    -h --help                     Show this screen.
    -e --end                      End current task.
    -f --file                     Open file with log.
    -s --script                   Open file with source code.
"""

from datetime import datetime, timedelta
from collections import defaultdict
import bisect
import docopt
import subprocess
import config
from config import logtime_path

import colors

DAYS_LEFT = 5
WEEK_GOAL = timedelta(hours=(5 * 8))
MONTH_GOAL = timedelta(hours=(4 * 5 * 8))

DATETIME_FORMAT = '%Y-%m-%d %H:%M'
TIME_FORMAT = '%H:%M'
COMMENT_INDICATOR = '#'
BREAK_INDICATOR = '@'
PROGESS_BAR_SIZE = 40

ZERO_TIME = timedelta()


class Printer(object):
    def today_summary(self, calendar):
        year = calendar.newest_year()
        month = year.newest_month()
        self._today_summary_month(month)
        week = month.newest_week()
        self._today_summary_week(week)
        day = week.newest_day()
        avg_time_for_days_left = timedelta(
            seconds=((WEEK_GOAL - (week.duration - day.duration)).total_seconds() / DAYS_LEFT)
        )
        self._progress_summary('today', day.duration, avg_time_for_days_left)
        self._today_summary_tasks(day)
        print ''
        print (
            datetime.now() + avg_time_for_days_left - day.duration
        ).strftime(TIME_FORMAT), colors.gray(datetime.now().strftime(TIME_FORMAT))

    def _today_summary_month(self, month):
        self._progress_summary('month', month.duration, MONTH_GOAL)

    def _today_summary_week(self, week):
        self._progress_summary('week ', week.duration, WEEK_GOAL)

    def _progress_summary(self, title, duration, goal):
        done = int(duration.total_seconds() / (goal.total_seconds() + 0.) * PROGESS_BAR_SIZE)
        remaining = PROGESS_BAR_SIZE - done
        if duration >= goal:
            print colors.on_green(PROGESS_BAR_SIZE * ' ')
        else:
            print colors.on_white(done * ' ') + colors.on_gray(' ' * remaining)
        print '{}   {} {} {}'.format(
            title,
            format_timedelta(duration),
            colors.gray('- ' + format_timedelta(goal) + ' ='),
            format_timedelta(goal - duration),
        )
        print ''

    def _today_summary_day(self, day):
        print 'today   {} {}= {} - {}{}'.format(
            format_timedelta(day.duration),
            colors.GRAY,
            format_timedelta(day.duration + day.break_duration),
            format_timedelta(day.break_duration),
            colors.DEFC,
        )

    def _today_summary_tasks(self, day):
        for task in day.iter_tasks():
            if task.is_current:
                print colors.blue('{} {} {}'.format(
                    format_timedelta(task.duration),
                    format_timedelta_for_redmine(task.duration),
                    task.title
                ))
            elif task.is_break:
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


def separate_timedelta(delta):
    hours = delta.total_seconds() / 3600.
    minutes = abs((hours - int(hours)) * 60)
    return int(hours), int(minutes)


def format_timedelta(delta):
    hours, minutes = separate_timedelta(delta)
    return '{}:{:02d}'.format(hours, minutes)


def format_timedelta_for_redmine(delta):
    hours, minutes = separate_timedelta(delta)
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
        comment = None
        for line in lines:
            if not line:
                continue
            if line.startswith(COMMENT_INDICATOR):
                comment = line
                continue
            yield self._parse_line(line)
        if comment:
            print comment

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

    def __init__(self, title, start, end):
        self.title = title
        self.start = start or self.DEFAULT_START_DATE
        self.end = end or datetime.now()
        self.is_current = not end

    @property
    def duration(self):
        return self.end - self.start

    @property
    def is_break(self):
        return self.title.startswith(BREAK_INDICATOR)

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


class CalendarKey(LogItem):
    def __init__(self, start):
        super(CalendarKey, self).__init__('', start=start, end=None)

    @staticmethod
    def now():
        return CalendarKey(datetime.now())


class SomeTime(object):
    def __init__(self):
        self.duration = timedelta()
        self.break_duration = timedelta()
        if self.subtime_class:
            self.subtimes = defaultdict(self.subtime_class)
        self.keys = []

    def add(self, logitem):
        self._add_duration(logitem)
        key = self.subtime_key(logitem)
        if key not in self.keys:
            bisect.insort_left(self.keys, key)
        self.subtimes[self.subtime_key(logitem)].add(logitem)

    def _add_duration(self, logitem):
        if logitem.is_break:
            self.break_duration += logitem.duration
        else:
            self.duration += logitem.duration

    def newest_subtime(self):
        return self.subtimes[self.keys[-1]]

    def get_day(self, some_datetime):
        sub = self.subtimes.get(self.subtime_key(some_datetime), None)
        if not sub:
            return None
        return sub.get_day(some_datetime)

    def all_tasks(self):
        for key in self.keys:
            for task in self.subtimes[key].all_tasks():
                yield task


class Task(SomeTime):
    subtime_class = None

    def __init__(self):
        self.logitems = []
        self.title = None
        self.duration = timedelta()
        self.is_current = False

    def add(self, logitem):
        self.title = logitem.title
        self.logitems.append(logitem)
        self.duration += logitem.duration
        self.is_current = self.is_current or logitem.is_current

    @property
    def is_break(self):
        return self.title.startswith(BREAK_INDICATOR)

    def all_tasks(self):
        return [self]


class Day(SomeTime):
    subtime_class = Task

    def subtime_key(self, logitem):
        return logitem.title

    def iter_tasks(self):
        for k in self.keys:
            yield self.subtimes[k]

    def get_day(self, some_datetime):
        return self


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


def start_task(title):
    new_line = make_timestamp() + '\n' + title
    append_line(new_line)


def end_task():
    new_line = make_timestamp()
    append_line(new_line)


def make_timestamp():
    return datetime.now().strftime(DATETIME_FORMAT)


def append_line(line):
    try:
        old = open(logtime_path).read()
    except IOError:
        old = ''
    if not old.endswith('\n'):
        line = '\n' + line
    open(logtime_path, 'a').write(line)


def summarize():
    Printer().today_summary(
        Calendar.from_file(logtime_path)
    )

if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)
    if arguments['<task_description>']:
        start_task(' '.join(arguments['<task_description>']))
    if arguments['--end']:
        end_task()
    if arguments['--file']:
        subprocess.call(['subl', logtime_path])
    if arguments['--script']:
        subprocess.call(['subl', config.logtime_script_path])
    summarize()
