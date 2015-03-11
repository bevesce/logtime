"""
Log and show time spent on tasks.
Using without argument will show logged time.
Using with some text will add new task.

Usage:
    logtime2.py [-w=<no_weeks>]
    logtime2.py [-n=<no_tasks>] <task_description>...
    logtime2.py -e
    logtime2.py -n=<no_tasks>
    logtime2.py -t=<task_num>
    logtime2.py -f

Options:
    -h --help                     Show this screen.
    -e --end                      End current task.
    -n=<no_tasks> --last_n_tasks  Show last <no_tasks> task with indices.
    -t=<task_num> --task          Return to task with <task_num> index.
    -w=<no_weeks> --weeks         How many weeks to display [default: 1].
    -f --file                     Open file with log.
"""
import datetime as dt
# Personal congif:
from config import logtime_path as path
time_to_work_in_week = dt.timedelta(hours=20)
time_to_work_in_day = {
    1: dt.timedelta(hours=7),  # Mon
    2: dt.timedelta(hours=5),  # Tue
    3: dt.timedelta(hours=8),  # Wed
    4: dt.timedelta(hours=8),  # Thu
    5: dt.timedelta(hours=8),  # Fri
    6: dt.timedelta(hours=0),  # Sat
    7: dt.timedelta(hours=0),  # Sun
}

break_indicator = '@'
# tasks with description starting
# with this text are considered breaks and are not
# counted to work time

import docopt
import re
from collections import defaultdict
import colors


ZERO_TIME = dt.timedelta()


def align_right(text, width=35):
    return text.rjust(width)


def ind(text, indention='  '):
    return indention + text


def format_timedelta(delta, align=False):
    H24 = dt.timedelta(hours=24)
    minus = False
    if delta < ZERO_TIME:
        # timedelta(hours=8) - timedelta(hours=9) = -1 day, 23:00:00
        # so it need to be flipped to 1 hour
        delta = H24 - delta
        minus = True
    hours = delta.seconds / 3600
    minutes = (delta.seconds % 3600) / 60
    if minus:
        return '-{}:{:02d}'.format(hours, minutes)
    elif align:
        return '{: 2d}:{:02d}'.format(hours, minutes)
    else:
        return '{}:{:02d}'.format(hours, minutes)


class Weeks(object):
    def __init__(self):
        self.weeks = defaultdict(Week)

    def add_task(self, start, end, description):
        self.weeks[self.get_week_num(start)].add_task(start, end, description)

    def get_week_num(self, date):
        return date.isocalendar()[:2]  # year and week to fully identify week

    def print_summary(self, no_weeks=1):
        sorted_weeks = sorted(self.weeks.items())[-no_weeks:]
        for _, week in sorted_weeks:
            week.print_summary()


class Week(object):
    def __init__(self):
        self.days = defaultdict(Day)
        self._duration = None

    def add_task(self, start, end, description):
        self.days[self.get_day(start)].add_task(start, end, description)

    def get_day(self, date):
        return date.isocalendar()[2]

    def print_summary(self):
        print self.format_title()
        for _, day in sorted(self.days.items()):
            day.print_summary()
        self.print_weekend()

    def format_title(self):
        text = align_right(format_timedelta(self.time_left()))
        color = colors.white_on_magenta if self.time_left() >= ZERO_TIME else colors.white_on_green
        return color(text)

    def time_left(self):
        return time_to_work_in_week - self.duration()

    def duration(self):
        if self.duration_already_calculated():
            return self._duration
        self._duration = self.sum_days_durations()
        return self._duration

    def duration_already_calculated(self):
        return self._duration

    def sum_days_durations(self):
        duration = dt.timedelta()
        for day in self.days.values():
            day.calculate_durations()
            duration += day.work_duration
        return duration

    def print_weekend(self):
        now = dt.datetime.now()
        weekend = now + self.time_left()
        c = colors.yellow
        if weekend <= now:
            c = colors.green
        print c(weekend.strftime('%F %R'))
        print colors.defc(now.strftime('%F %R'))


class Day(object):
    time_pattern = '%H:%M'

    def __init__(self):
        self.tasks = defaultdict(Task)
        self.start = None
        self.end = None
        self.number = None
        self.duration = None
        self.work_duration = None
        self.break_duration = None

    def add_task(self, start, end, description):
        self.tasks[description].add_time(start, end, description)
        self.min_start(start)
        self.max_end(end)

    def min_start(self, new_start):
        self.start = min(self.start, new_start) if self.start else new_start
        self.number = self.start.isocalendar()[2]

    def max_end(self, new_end):
        self.end = max(self.end, new_end) if self.end else new_end

    def print_summary(self):
        self.calculate_durations()
        self.print_title()
        self.print_stats()
        print ''
        self.print_tasks()
        print ''

    def print_title(self):
        print colors.on_blue(align_right(self.start.strftime('%Y-%m-%d')))

    def print_stats(self):
        print ind(self.formated_worked())
        print ind(self.formated_start())
        print ind(self.formated_end())
        print ind(self.formated_time_left())

    def print_tasks(self):
        for task in sorted(self.tasks.values(), key=lambda t: t.description)[::-1]:
            task.print_summary()

    def formated_start(self):
        return 'Start  {}'.format(self.start.strftime(self.time_pattern))

    def formated_end(self):
        this_day = time_to_work_in_day[self.number]
        end = (self.start + this_day + self.break_duration).strftime(self.time_pattern)
        return 'End    {}'.format(end)

    def formated_time_left(self):
        color = colors.green if self.time_left() <= ZERO_TIME else colors.blue
        return color('Left   {}'.format(
            format_timedelta(self.time_left(), align=True)
        ))

    def time_left(self):
        this_day = time_to_work_in_day[self.number]
        return this_day - self.work_duration

    def formated_worked(self):
        return 'Worked {} = {} - {}'.format(
            self.formated_work_duration(),
            format_timedelta(self.duration),
            format_timedelta(self.break_duration),
        )

    def formated_work_duration(self):
        return format_timedelta(self.work_duration, align=True)

    def calculate_durations(self):
        if all([self.duration, self.work_duration, self.break_duration]):
            return
        self.duration = ZERO_TIME
        self.work_duration = ZERO_TIME
        self.break_duration = ZERO_TIME
        for task in self.tasks.values():
            self.work_duration += task.duration_work()
            self.break_duration += task.duration_break()
            self.duration += task.duration()


class Task(object):
    def __init__(self, description=None):
        self._duration = dt.timedelta()
        self.description = description
        self.start = None
        self.end = None

    def add_time(self, start, end, description=None):
        self.description = description or self.description
        self.is_break = self._check_if_break(description)
        self._duration += end - start
        self.start = min(self.start, start) if self.start else start
        self.end = min(self.end, end) if self.end else end

    def _check_if_break(self, description):
        return description.startswith(break_indicator)

    def duration(self):
        return self._duration

    def duration_work(self):
        if self.is_break:
            return dt.timedelta()
        else:
            return self.duration()

    def duration_break(self):
        if self.is_break:
            return self.duration()
        else:
            return dt.timedelta()

    def print_summary(self):
        print ind(self.formated_duration() + ' ' + self.description)

    def formated_duration(self):
        return format_timedelta(self._duration)


class Log(object):
    full_line_template = '{start} > {end} : {description}'
    full_line_pattern = re.compile(
        r'(\d\d\d\d-\d\d-\d\d \d\d:\d\d) > (\d\d\d\d-\d\d-\d\d \d\d:\d\d) : (.*)'
    )
    not_ended_line_template = '{start} : {description}'
    not_ended_line_pattern = re.compile(
        r'(\d\d\d\d-\d\d-\d\d \d\d:\d\d) : (.*)'
    )
    time_pattern = '%Y-%m-%d %H:%M'

    def __init__(self, path=path):
        self.path = path
        self._lines = self._read_lines()
        self._now = dt.datetime.now()

    def _read_lines(self):
        try:
            with open(path, 'r') as f:
                log = f.read().splitlines()
        except IOError:
            open(path, 'w').close()
            log = []
        return log

    def add_task(self, description):
        self.end()
        self._lines.append(self._format_new_task(description))

    def end(self):
        if not self._last_line_is_ended():
            self._end_last_line()

    def repeat_task(self, task_index):
        task_index += 1
        task_line = self._lines[-task_index]
        description = self.get_desciption(task_line)
        if description:
            self.add_task(description)

    def get_desciption(self, line):
        full_line_match = self.full_line_pattern.match(line)
        if full_line_match:
            return full_line_match.group(3)
        not_ended_line_match = self.not_ended_line_pattern.match(line)
        if not_ended_line_match:
            return not_ended_line_match.group(2)

    def _last_line_is_ended(self):
        if self._lines:
            return not self.not_ended_line_pattern.match(self._lines[-1])
        else:
            return False

    def _end_last_line(self):
        if self._lines:
            match = self.not_ended_line_pattern.match(self._lines[-1])
            self._lines[-1] = self._format_full_task(
                start=match.group(1),
                description=match.group(2),
                end=self._now.strftime(self.time_pattern),
            )

    def _format_full_task(self, description, start, end):
        return self.full_line_template.format(
            start=start, description=description, end=end
        )

    def _format_new_task(self, description):
        return self.not_ended_line_template.format(
            start=self._now.strftime(self.time_pattern),
            description=description
        )

    def save(self):
        with open(path, 'w') as f:
            f.write('\n'.join(self._lines))

    def print_summary(self, no_weeks=1):
        self._parse()
        self.weeks.print_summary(no_weeks)

    def _parse(self):
        self.weeks = Weeks()
        for line in self._lines:
            start, end, description = None, None, None
            match = self.full_line_pattern.match(line)
            half_match = self.not_ended_line_pattern.match(line)
            if match:
                start, end = self._parse_dates_from_match(match)
                description = self._desciption_from_match(match)
            elif half_match:
                    start, end = self._parse_date_from_half_match(half_match)
                    description = self._desciption_from_half_match(half_match)
            if start and end:
                self.weeks.add_task(start, end, description)

    def _parse_dates_from_match(self, match):
        return (
            dt.datetime.strptime(match.group(1), self.time_pattern),
            dt.datetime.strptime(match.group(2), self.time_pattern)
        )

    def _parse_date_from_half_match(self, match):
        return (
            dt.datetime.strptime(match.group(1), self.time_pattern),
            dt.datetime.now()
        )

    def _desciption_from_match(self, match):
        return match.group(3)

    def _desciption_from_half_match(self, match):
        return match.group(2)

    def show_short(self, no_tasks):
        if no_tasks == 0:
            return
        print '\n'.join(
            ['{}: {}'.format(no_tasks - i - 1, l) for i, l in enumerate(self._lines[-no_tasks:])]
        )


if __name__ == '__main__':
    log = Log()
    arguments = docopt.docopt(__doc__)
    last_n_tasks = int(arguments['--last_n_tasks'] if arguments['--last_n_tasks'] else 5)
    if arguments['<task_description>']:
        log.add_task(
            description=' '.join(arguments['<task_description>']),
        )
        log.save()
        log.show_short(last_n_tasks)
    elif arguments['--task']:
        task_num = int(arguments['--task'])
        log.repeat_task(task_num)
        log.save()
        log.show_short(last_n_tasks)
    elif arguments['--last_n_tasks']:
        log.show_short(last_n_tasks)
    elif arguments['--end']:
        log.end()
        log.save()
        log.show_short(last_n_tasks)
    elif arguments['--file']:
        import subprocess
        subprocess.call(['subl', path])
    else:
        log.print_summary(no_weeks=int(arguments['--weeks']))
