# -*- coding: utf-8 -*-
#!/usr/bin/env python2

"""
Log and show time spent on tasks.
Using without argument will show logged tasks with time spent on them.
Using with some text will start new task.

Usage:
    logtime.py <task_description>...
    logtime.py -e
    logtime.py -f
    logtime.py -s
    logtime.py -l
    logtime.py -r
    logtime.py -t <task_description>...
    logtime.py -p <prefix>...
    logtime.py

Options:
    -h --help                     Show this screen.
    -e --end                      End current task.
    -f --file                     Open file with log.
    -s --script                   Open file with source code.
    -l --loop                     Loooopy
    -t --time                     Time me, 25 minutes for tasks, 5 minutes for breaks
    -p --prefix                   Takes task prefix and show statistic about matching tasks
    -r --recent                   Show most recent task
"""

from __future__ import unicode_literals

from datetime import datetime, timedelta
from collections import defaultdict
import bisect
import docopt
import subprocess
import config
from config import logtime_path
try:
    import timer
    import colors
except:
    pass

DATETIME_FORMAT = '%Y-%m-%d %H:%M'
TIME_FORMAT = '%H:%M'
COMMENT_INDICATOR = '%'
BREAK_INDICATOR = '@'
PROGESS_BAR_SIZE = 50

ZERO_TIME = timedelta()

try:
    class Printer():
        def today_summary(self, calendar):
            today = None
            days = list(calendar.iter_days())
            goal = variables.goal('d')
            if not days:
                print('NOPE :(')
                return
            for day in days[:-1]:
                self._progress_bar(
                    day.duration, goal
                )
            today = days[-1]
            self._progress_bar(
                today.duration,
                goal,
                highlight=colors.on_blue
            )
            end_time = datetime.now() + (goal - today.duration)
            can_end_today = end_time.strftime('%F') == datetime.now().strftime('%F')
            if can_end_today:
                print(end_time.strftime('%F %R'))
            else:
                print(':(')
            print('')
            self._summary_tasks(calendar)

        def _progress_bar(self, duration, goal, highlight=colors.on_white):
            if not goal:
                return
            progess_bar_size = PROGESS_BAR_SIZE - 12
            done = int(duration.total_seconds() / (goal.total_seconds() + 0.) * progess_bar_size)
            done = max(done, 0)
            remaining = progess_bar_size - done
            remaining = min(progess_bar_size, remaining)
            remaining = max(remaining, 0)
            print('{} {} {}{}'.format(
                colors.gray(format_timedelta(duration)),
                format_timedelta(goal - duration),
                highlight(done * ' '),
                colors.on_gray(' ' * remaining),
            ))

        def _how_much_left_if_i_leave_now(self, goal, days_left):
            if days_left == 1:
                return '*'
            return format_timedelta(
                goal / (days_left - 1)
            )

        def _summary_tasks(self, day):
            for task in day.iter_tasks():
                if task.is_current:
                    self._print_current_task(task)
                elif task.is_break:
                    self._print_break(task)
                else:
                    self._print_task(task)

        def _print_current_task(self, task):
            self._print_task(task, colors.blue)

        def _print_break(self, task):
            self._print_task(task, colors.gray)

        def _print_task(self, task, color=colors.defc):
            left = '{} {}'.format(
                format_timedelta(task.duration),
                task.title
            )
            print('{}'.format(
                color(left),
            ))
except:
    pass


def separate_timedelta(delta):
    hours = delta.total_seconds() / 3600.
    minutes = abs((hours - int(hours)) * 60)
    return int(hours), int(minutes)


def format_timedelta(delta):
    hours, minutes = separate_timedelta(delta)
    return '{:02d}:{:02d}'.format(hours, minutes)


def format_timedelta_for_redmine(delta):
    hours, minutes = separate_timedelta(delta)
    minutes = '{:.3f}'.format(minutes / 60.)
    return '{}.{}'.format(hours, minutes[2:])


def calculate_day_goal(month, week, day):
    switcher = variables.s
    bigger = month if switcher == 'm' else week
    seconds_left = (variables.goal(switcher) - bigger.duration + day.duration).total_seconds()
    avg_day_left = timedelta(seconds=(seconds_left / variables.dl))
    day_goal = variables.goal('d') or avg_day_left
    return day_goal


class VariablesHandler(object):
    def __init__(self):
        self.variables = {}
        self.defaults = {
            'm': 3 / 5 * 4 * 5 * 8,
            'w': 3 * 8,
            'd': 8,
            'dl': 1,
            's': 'w'
        }

    def set(self, text):
        try:
            key, value = text.split('=')
        except:
            return
        key, value = key.strip(), value.strip()
        self.variables[key] = self._parse_value(value)

    def _parse_value(self, value):
        try:
            return eval(value)
        except NameError:
            return value

    def __getattr__(self, k):
        default = self.defaults.get(k)
        return self.variables.get(k, default)

    def goal(self, k):
        v = getattr(self, k)
        if isinstance(v, timedelta):
            return v
        try:
            return timedelta(hours=v)
        except TypeError:
            return v

variables = VariablesHandler()


class Parser(object):
    def __init__(self, text):
        self.text = text.strip()

    def parse(self):
        for start, title, end in self._parse_to_raw():
            yield LogItem(title, start=start, end=end)

    def _parse_to_raw(self):
        prev_date, prev_title = None, None
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
            if not line:
                continue
            if line.startswith(COMMENT_INDICATOR):
                variables.set(line[len(COMMENT_INDICATOR):])
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
    DEFAULT_START_DATE = datetime(1900, 1, 1, 0, 0)

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
        self._update_start(logitem)
        self._add_duration(logitem)
        key = self.subtime_key(logitem)
        if key not in self.keys:
            bisect.insort_left(self.keys, key)
        self.subtimes[key].add(logitem)

    def _update_start(self, logitem):
        self.start = max(logitem.start, self.start) if hasattr(self, 'start') else logitem.start

    def _add_duration(self, logitem):
        if logitem.is_break:
            self.break_duration += logitem.duration
        else:
            self.duration += logitem.duration

    def newest_subtime(self):
        return self.subtimes[self.keys[-1]]

    def get_day(self, some_datetime):
        if not isinstance(some_datetime, LogItem):
            some_datetime = LogItem('', some_datetime, some_datetime)
        sub = self.subtimes.get(self.subtime_key(some_datetime), None)
        if not sub:
            return None
        return sub.get_day(some_datetime)

    def all_tasks(self):
        for key in self.keys:
            for task in self.subtimes[key].all_tasks():
                yield task

    def iter_days(self):
        for k in self.keys:
            for day in self.subtimes[k].iter_days():
                yield day

    def iter_tasks(self):
        tasks = defaultdict(Task)
        for k in self.keys:
            for task in self.subtimes[k].iter_tasks():
                t = tasks[task.title]
                t.title = task.title
                t.duration += task.duration
                t.is_current = t.is_current or task.is_current
        tasks = sorted(tasks.values(), key=lambda t: t.title)
        for task in tasks:
            yield task


class Task(SomeTime):
    subtime_class = None

    def __init__(self):
        self.logitems = []
        self.title = None
        self.duration = timedelta()
        self.is_current = False

    def add(self, logitem):
        self._update_start(logitem)
        self.title = logitem.title
        self.logitems.append(logitem)
        self.duration += logitem.duration
        self.is_current = self.is_current or logitem.is_current

    @property
    def is_break(self):
        return self.title.startswith(BREAK_INDICATOR)

    def all_tasks(self):
        return [self]

    def iter_days(self):
        raise TypeError("Task can't iterate days")

    def iter_tasks(self):
        yield self


class Day(SomeTime):
    subtime_class = Task

    def subtime_key(self, logitem):
        return logitem.title

    def iter_tasks(self):
        for k in self.keys:
            yield self.subtimes[k]

    def get_day(self, some_datetime):
        return self

    def iter_days(self):
        yield self


class Week(SomeTime):
    subtime_class = Day

    def subtime_key(self, logitem):
        return logitem.day

    def newest_day(self):
        return self.newest_subtime()

    def days(self):
        for st in self.subtimes.values():
            yield st


class Month(SomeTime):
    subtime_class = Week

    def subtime_key(self, logitem):
        return logitem.week

    def newest_week(self):
        return self.newest_subtime()

    def weeks(self):
        for st in self.subtimes.values():
            yield st

    def days(self):
        for w in self.weeks():
            for d in w.days():
                yield d


class Year(SomeTime):
    subtime_class = Month

    def subtime_key(self, logitem):
        return logitem.month

    def newest_month(self):
        return self.newest_subtime()


class Calendar(SomeTime):
    subtime_class = Year

    @classmethod
    def from_text(cls, text):
        return Calendar(Parser(text).parse())

    @classmethod
    def from_file(cls, path):
        with open(logtime_path) as f:
            return Calendar.from_text(f.read())

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
    if title.startswith(COMMENT_INDICATOR):
        new_line = title
    else:
        new_line = make_timestamp() + '\n' + title
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


def summarize():
    Printer().today_summary(
        Calendar.from_file(logtime_path)
    )
    print('_' * PROGESS_BAR_SIZE)
    print(datetime.now().strftime('%F %R'))


def summarize_tasks(prefix):
    calendar = Calendar.from_file(logtime_path)
    time_sum = timedelta(0)
    for task in calendar.all_tasks():
        if task.title.startswith(prefix):
            time_sum += task.duration
    goal = variables.goal(prefix)
    if goal:
        Printer()._progress_bar(time_sum, goal)
    else:
        print(format_timedelta(time_sum))


def timeit(task):
    if task.startswith(BREAK_INDICATOR):
        timer.start(5, scale=5, additional_print=summarize)
    else:
        timer.start(25, scale=2, additional_print=summarize)


def maybe_timeit(arguments, task):
    if arguments['--time']:
        try:
            timeit(task)
        except KeyboardInterrupt:
            end_task()
            summarize()
            print('END')
            import sys
            sys.exit(0)


if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)
    if arguments['<task_description>']:
        task = ' '.join(arguments['<task_description>'])
        start_task(task)
        maybe_timeit(arguments, task)
    if arguments['--end']:
        end_task()
    if arguments['--file']:
        subprocess.call(['subl', logtime_path])
    if arguments['--script']:
        subprocess.call(['subl', config.logtime_script_path])
    if arguments['--loop']:
        import time
        while True:
            print('\n' * 100)
            summarize()
            time.sleep(60)
    if arguments['--prefix']:
        prefix = ' '.join(arguments['<prefix>'])
        summarize_tasks(prefix)
        import sys
        sys.exit(0)
    if arguments['--recent']:
        c = Calendar.from_file(logtime_path)
        current = [t for t in c.all_tasks() if t.is_current]
        current = current[0] if current else None
        if current:
            print(
                '{} | {}'.format(
                    current.title, format_timedelta(current.duration)
                )
            )
        else:
            print(u'?')
        import sys
        sys.exit(0)
    summarize()
