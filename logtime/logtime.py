from collections import defaultdict
from datetime import timedelta
from datetime import datetime
import re

from .parse_date import parse_date

TIME_FORMAT = '%M'
DATETIME_FORMAT = '%Y-%m-%d %H:%M'
COMMENT_PREFIX = '# '
DESCRIPTION_SEPARATOR = '/'
WHITESPACED_DESCRIPTION_SEPARATOR = ' ' + DESCRIPTION_SEPARATOR + ' '
REVERSE_ORDER_PREFIX = '-'


class LogtimeError(Exception):
    pass


class LogItem:
    def __init__(self, start, end, tags):
        self.start = start
        self.end = end or datetime.now()
        self.ended = bool(end)
        self.tags = tuple(t.strip() for t in tags)
        if self.end < self.start:
            raise LogtimeError("Wrong logitem, end datetime can't be smaller than start:\n{}".format(self))

    def __str__(self, include_end=True):
        text = '{}\n{}'.format(
            self.start.strftime(DATETIME_FORMAT),
            WHITESPACED_DESCRIPTION_SEPARATOR.join(self.tags),
        )
        if include_end:
            text += '\n{}'.format(self.end.strftime(DATETIME_FORMAT))
        return text

    def __repr__(self):
        return 'LogItem({}, {}, {})'.format(
            self.start, self.end, self.tags
        )

    def __eq__(self, other):
        return all([
            self.start == other.start,
            self.end == other.end,
            self.tags == other.tags,
            self.get_description() == other.get_description()
        ])

    def get_duration(self):
        return self.end - self.start

    def get_description(self):
        return WHITESPACED_DESCRIPTION_SEPARATOR.join(self.tags)

    def cut_to_dates(self, start, stop):
        if stop and stop < self.start:
            return None
        elif start and start > self.end:
            return None
        return LogItem(
            max(start, self.start) if start else self.start,
            min(stop, self.end) if stop else self.end,
            self.tags
        )


class Log:
    def __init__(self, logitems):
        if isinstance(logitems, str):
            logitems = self._parse(logitems)
        try:
            self._logitems = tuple(logitems)
        except TypeError as e:
            self._logitems = (logitems, )

    @staticmethod
    def _parse(text):
        return LogItemsParser.parse_text(text)

    def __str__(self):
        text = '\n'.join(i.__str__(include_end=False) for i in self)
        if self and self._logitems[-1].ended:
            text += '\n{}'.format(self.get_end().strftime(DATETIME_FORMAT))
        return text

    def __eq__(self, other):
        return set(self._logitems) == set(other._logitems)

    def __len__(self):
        return len(self._logitems)

    def __iter__(self):
        for logitem in self._logitems:
            yield logitem

    def __getitem__(self, datetime_slice):
        if not isinstance(datetime_slice, slice):
            raise LogtimeError('You can subscribe Log only by slice. {}'.format(datetime_slice))
        result = []
        start = parse_date(datetime_slice.start) or self.get_start()
        stop = parse_date(datetime_slice.stop) or self.get_end()
        step = datetime_slice.step
        if step:
            while start < stop:
                next_start = start + step if isinstance(step, timedelta) else step(start)
                result.append(Log(self.yield_cut_to_dates(start, next_start)))
                start = next_start
        else:
            return Log(self.yield_cut_to_dates(start, stop))
        return tuple(result)

    def __truediv__(self, f):
        return self.filter(f)

    def filter(self, f):
        if isinstance(f, str):
            from . import query
            return query.parse(f).filter(self)
        return Log(l for l in self._logitems if f(l))

    def yield_cut_to_dates(self, start, stop):
        for logitem in self._logitems:
            cut = logitem.cut_to_dates(start, stop)
            if cut:
                yield cut

    def map(self, f):
        return Log(f(i) for i in self)

    def sum(self):
        return sum((i.get_duration() for i in self), timedelta())

    def total_seconds(self):
        return self.sum().total_seconds()

    def total_hours(self):
        return self.total_seconds() / 3600

    def sorted(self, key, reverse=False):
        return Log(sorted(
            self._logitems, key=key, reverse=reverse
        ))

    def get_start(self):
        if (len(self) == 0):
            return datetime.now()
        return min(l.start for l in self)

    def get_end(self):
        if (len(self) == 0):
            return datetime.now()
        return max(l.end for l in self)


class LogItemsParser:
    @classmethod
    def parse_text(cls, text):
        lines = text.splitlines()
        return cls.parse_lines(lines)

    @classmethod
    def parse_lines(cls, lines):
        start, end, description = None, None, None
        for line in lines:
            if line.startswith(COMMENT_PREFIX):
                continue
            start, end, description = cls.advance_start_end_description(
                line, start, end, description
            )
            if start and end and description:
                yield LogItem(
                    start, end, description.split(DESCRIPTION_SEPARATOR)
                )
                start, end, description = end, None, None
        if start and description:
            yield LogItem(start, None, description.split(DESCRIPTION_SEPARATOR))

    @classmethod
    def advance_start_end_description(cls, line, start, end, description):
        maybe_date = cls.parse_date(line)
        if maybe_date:
            if start and description:
                end = maybe_date
            else:
                start = maybe_date
        elif line:
            description = line
        return start, end, description

    @classmethod
    def parse_date(cls, line):
        try:
            return datetime.strptime(line, DATETIME_FORMAT)
        except ValueError:
            return None
