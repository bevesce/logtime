from datetime import datetime
from datetime import timedelta
import math
from . import colors

PROGRESS_TEMPLATE = """{bar}
done: {done}
left: {left}
goal: {goal}"""


def print_progress(done, goal, width=50):
    try:
        done = done.sum()
    except AttributeError:
        pass
    print(PROGRESS_TEMPLATE.format(
        left=colors.blue(format_timedelta(goal - done)),
        done=colors.green(format_timedelta(done)),
        goal=colors.gray(format_timedelta(goal)),
        bar=progress_bar(done.total_seconds() / goal.total_seconds(), width)
    ))


def progress_bar(fill_ratio, width=50):
    if fill_ratio >= 1:
        return colors.on_green(' ' * width)
    fill_size = math.floor(fill_ratio * width)
    rest_size = width - fill_size
    return colors.on_green(' ' * fill_size) + colors.on_blue(' ' * rest_size)


def print_timeline(logitems, start, end, interval=timedelta(minutes=15)):
    current = start
    while current < end:
        def f(logitem):
            return logitem.start <= current and logitem.start >= current - interval
        print(colors.blue(current), ', '.join(l.get_description() for l in logitems.filter(f)))
        current += interval


def print_breakdown(logitems):
    def by_tag(index):
        def f(logitem):
            try:
                return logitem.tags[index]
            except IndexError:
                return '_'
        return f

    for i in range(0, 4):
        logitems = logitems.group(by_tag(i))
    print(logitems.str(skip='_'))


def format_timedelta(delta):
    hours, minutes = get_hours_and_minutes(delta)
    return '{:02d}:{:02d}'.format(hours, minutes)


def get_hours_and_minutes(delta):
    hours = delta.total_seconds() / 3600.
    minutes = abs((hours - int(hours)) * 60)
    return int(hours), int(minutes)


def get_week(date):
    return '{}-{:02d}'.format(
        date.year, date.isocalendar()[1]
    )