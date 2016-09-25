import notes
import math
import colors
from logtime import Log
from logtime import Variables
from logtime import LogItem
from datetime import timedelta
from datetime import datetime

logtext = notes.read('logtime.txt')
l = Log(logtext)
v = Variables(logtext)

def progress_bar(fill_ratio, width=20):
    if fill_ratio >= 1:
        return colors.on_green(' ' * width)
    fill_size = math.floor(fill_ratio * width)
    rest_size = width - fill_size
    return colors.on_white(' ' * fill_size) + colors.on_gray(' ' * rest_size)


def complition_summary(done, goal, title):
    return '{title} {done}/{goal} {bar}'.format(
        title=title,
        done=format_timedelta(done),
        goal=format_timedelta(goal),
        bar=progress_bar(done.seconds / goal.seconds)
    )


def by_month(logitem):
    return month(logitem.date)


def month(date):
    return date.strftime('%Y-%m')


def separate_timedelta(delta):
    hours = delta.total_seconds() / 3600.
    minutes = abs((hours - int(hours)) * 60)
    return int(hours), int(minutes)


def format_timedelta(delta):
    hours, minutes = separate_timedelta(delta)
    return '{:02d}:{:02d}'.format(hours, minutes)


def week(date):
    return '{}-{:02d}'.format(
        date.year, date.isocalendar()[1]
    )

now = datetime.now()
this_week = l.filter(lambda i: week(now) == week(i.start))
today = this_week.filter(lambda i: i.start.day == now.day)
print(
    complition_summary(
        this_week.sum(),
        v.hours('week ' + week(now), 'week'),
        'WEEK'
    )
)
print(
    complition_summary(
        today.sum(),
        v.hours(datetime.now().strftime('%Y-%m-%d'), 'day'),
        ' DAY'
    )
)
print('')
print(this_week.group(lambda i: i.description()).sum())
