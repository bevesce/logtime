from collections import defaultdict
from datetime import timedelta
from datetime import datetime
import re

TIME_FORMAT = '%M'
DATETIME_FORMAT = '%Y-%m-%d %H:%M'
COMMENT_PREFIX = '# '
DESCRIPTION_SEPARATOR = '/'
WHITESPACED_DESCRIPTION_SEPARATOR = ' ' + DESCRIPTION_SEPARATOR + ' '
REVERSE_ORDER_PREFIX = '-'


class LogItem:
    def __init__(self, start, end, tags):
        self.start = start
        self.end = end or datetime.now()
        self.ended = bool(end)
        self.tags = tuple(t.strip() for t in tags)

    def __str__(self):
        return '{}\n{}\n{}'.format(
            self.start.strftime(DATETIME_FORMAT),
            WHITESPACED_DESCRIPTION_SEPARATOR.join(self.tags),
            self.end.strftime(DATETIME_FORMAT),
        )

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
        return '\n'.join(str(i) for i in self)

    def __eq__(self, other):
        return set(self._logitems) == set(other._logitems)

    def __len__(self):
        return len(self._logitems)

    def __iter__(self):
        for logitem in self._logitems:
            yield logitem

    def __getitem__(self, slice):
        return Log(self.yield_cut_to_dates(slice.start, slice.stop))

    def filter(self, f):
        if isinstance(f, str):
            from . import query
            return query.parse(f).filter(self)
        return Log(l for l in self._logitems if l)

    def yield_cut_to_dates(self, start, stop):
        for logitem in self._logitems:
            cut = logitem.cut_to_dates(start, stop)
            if cut:
                yield cut

    def map(self, f):
        return Log(f(i) for i in self)

    def group(self, key):
        key = {
            'year': lambda i: i.start.strftime('%Y'),
            'month': lambda i: i.start.strftime('%m'),
            'day': lambda i: i.start.strftime('%d'),
            'date': lambda i: i.start.strftime('%F'),
            'year-month': lambda i: i.start.strftime('%Y-%m'),
            'week': lambda i: i.start.strftime('%W'),
            'year-week': lambda i: i.start.strftime('%Y-%W'),
        }.get(key, key)
        if isinstance(key, int):
            index = key
            def key(o):
                return o.tags[index]
        result = defaultdict(list)
        for i in self:
            result[key(i)].append(i)
        return GroupedLog({
            k: Log(v) for k, v in result.items()
        })

    def sum(self):
        return sum((i.get_duration() for i in self), timedelta())

    def sorted(self, key, reverse=False):
        return Log(sorted(
            self._logitems, key=key, reverse=reverse
        ))

    def get_start(self):
        return min(l.start for l in self)

    def get_end(self):
        return max(l.end for l in self)


def get_from_list(l, index, default=None):
    try:
        l[index]
    except:
        return default


class GroupedLog:
    def __init__(self, groups):
        self._groups = groups

    def __eq__(self, other):
        if set(self.groups()) != set(other.groups()):
            return False
        for group in self.groups():
            if self._groups[group] != other._groups[group]:
                return False
        return True

    def __str__(self):
        return self.str()

    def str(self, indent=0, skip=None, format_timedelta=None):
        def sum_sub(v):
            if isinstance(v, Log):
                return v.sum()
            else:
                return sum((sum_sub(vv) for vv in v.values()), timedelta())

        def str_sub(v):
            if isinstance(v, Log):
                return ''
            else:
                if list(v.keys()) == [skip]:
                    return ''
                return '\n' + v.str(indent=indent + 1, skip=skip, format_timedelta=format_timedelta)
        def f(s):
            if format_timedelta:
                return format_timedelta(s)
            return s
        return '\n'.join(
            '{}{} = {}{}'.format('    ' * indent, k, f(sum_sub(self._groups[k])), str_sub(self._groups[k]))
            for k in sorted(self._groups.keys())
        )


    def map(self, f):
        return GroupedLog({
            k: v.map(f) for k, v in self._groups.items()
        })

    def filter(self, f):
        return GroupedLog({
            k: v.filter(f) for k, v in self._groups.items()
        })

    def sum(self):
        return GroupedTime({
            k: v.sum() for k, v in self._groups.items()
        })

    def group(self, key):
        return GroupedLog({
            k: v.group(key) for k, v in self._groups.items()
        })

    def items(self):
        return self._groups.items()

    def values(self):
        return self._groups.values()

    def keys(self):
        return self._groups.keys()


class GroupedTime:
    def __init__(self, groups):
        self._groups = groups

    def __eq__(self, other):
        if set(self.groups()) != set(other.groups()):
            return False
        for category in self.groups():
            if self._groups[category] != other._groups[category]:
                return False
        return True

    def __str__(self):
        return '\n'.join(
            '{} = {}'.format(k, v) for k, v in self._groups.items()
        )

    def __getitem__(self, category):
        return self._groups[category]

    def sum(self):
        def f(v):
            if isinstance(v, GroupedTime):
                return v.sum()
            return v
        return sum((f(v) for v in self.values()), timedelta())

    def groups(self):
        return self._groups.keys()

    def items(self):
        return self._groups.items()

    def values(self):
        return self._groups.values()


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


class Variables:
    def __init__(self, text):
        self._variables = {}
        p = re.compile(r'# (.*) = (.*)')
        for k, v in p.findall(text):
            self._variables[k] = v

    def hours(self, *keys):
        for key in keys:
            if key in self._variables:
                return timedelta(hours=int(self._variables[key]))
        raise KeyError('none key works: {}'.format(keys))
