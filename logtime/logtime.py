from collections import defaultdict
from datetime import timedelta
from datetime import datetime
import re

from . import query

TIME_FORMAT = '%M'
DATETIME_FORMAT = '%Y-%m-%d %H:%M'
COMMENT_PREFIX = '# '
DESCRIPTION_SEPARATOR = ' - '
REVERSE_ORDER_PREFIX = '-'


class LogItem:
    def __init__(self, start, end, tags):
        self.start = start
        self.end = end
        self.tags = tags

    def __str__(self):
        return '{}\n{}\n{}'.format(
            self.start.strftime(DATETIME_FORMAT),
            ' - '.join(self.tags),
            self.end.strftime(DATETIME_FORMAT),
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
        return DESCRIPTION_SEPARATOR.join(self.tags)


class Log:
    def __init__(self, logitems):
        if isinstance(logitems, str):
            logitems = self._parse(logitems)
        self._logitems = tuple(logitems)

    @staticmethod
    def _parse(text):
        return LogItemsParser.parse_text(text)

    def __str__(self):
        return '\n'.join(str(i) for i in self)

    def __eq__(self, other):
        return set(self._logitems) == set(other._logitems)

    def __len__(self):
        return len(self._logitems)

    def __getitem__(self, index):
        return self._logitems[index]

    def filter(self, f):
        if isinstance(f, str):
            f = query.parse(f)
        return Log(self._join(
            i for i in self._split_by_minute() if f(i)
        ))

    @staticmethod
    def _join(logitems):
        joined = {}
        changed = True
        while changed:
            joined = {}
            changed = False
            for item in logitems:
                if item.start in joined and item.tags == joined[item.start].tags:
                    item2 = joined.pop(item.start)
                    newitem = Log._join_items(item, item2)
                    joined[newitem.end] = newitem
                    changed = True
                else:
                    joined[item.end] = item
            logitems = joined.values()
        return joined.values()

    @staticmethod
    def _join_items(item1, item2):
        return LogItem(
            min(item1.start, item2.start),
            max(item1.end, item2.end),
            item1.tags
        )

    def _split_by_minute(self):
        for i in self:
            end = i.end
            start = i.start
            while start < end:
                next_start = start + timedelta(minutes=1)
                yield LogItem(start, next_start, i.tags)
                start = next_start

    def map(self, f):
        return Log(f(i) for i in self)

    def group(self, key):
        if isinstance(key, str):
            key = query.parse(key)
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
        return '\n'.join(
            '# {}\n{}'.format(k, v)
            for k, v in self._groups.items()
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


class GroupedTime:
    def __init__(self, groups):
        self._categories = groups

    def __eq__(self, other):
        if set(self.groups()) != set(other.groups()):
            return False
        for category in self.groups():
            if self._categories[category] != other._categories[category]:
                return False
        return True

    def __str__(self):
        return '\n'.join(
            '{} = {}'.format(k, v) for k, v in self._categories.items()
        )

    def __getitem__(self, category):
        return self._categories[category]

    def groups(self):
        return self._categories.keys()


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
                yield LogItem(start, end, description.split(DESCRIPTION_SEPARATOR))
                start, end, description = end, None, None
        if start and description:
            yield LogItem(start, datetime.now(), description.split(DESCRIPTION_SEPARATOR))

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
