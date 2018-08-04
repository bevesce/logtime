from .logtime import LogItemsParser
from .logtime import LogItem

from .logtime import DATETIME_FORMAT
from .logtime import WHITESPACED_DESCRIPTION_SEPARATOR


class FixingLogItem(LogItem):
    def __init__(self, start, end, tags):
        self.start = start
        self.end = end
        self.tags = tuple(t.strip() for t in tags)
        self.max_end = end

    def str(self, next):
        result = self.start.strftime(DATETIME_FORMAT)
        result += '\n' + WHITESPACED_DESCRIPTION_SEPARATOR.join(self.tags)
        if next and self.end < next.start and self.start <= self.end:
            result += '\n' + self.end.strftime(DATETIME_FORMAT)
        return result

def fix(log_text):
    fixing_log_items = list(LogItemsParser(FixingLogItem).parse_text(log_text))
    fixing_log_items.sort(key=lambda l: l.start)
    fixing_log_items_with_nexts = zip(fixing_log_items, fixing_log_items[1:] + [None])
    fixed_log_text = '\n'.join(
        l.str(next) for l, next in fixing_log_items_with_nexts
    )
    max_end = max(*(l.end for l in fixing_log_items if l.end))
    last_item = fixing_log_items[-1]
    if last_item.end and last_item.end < max_end:
        fixed_log_text += '\n' + max_end.strftime(DATETIME_FORMAT)
    return fixed_log_text
