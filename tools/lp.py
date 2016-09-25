import sys

from selector import select, make_fuzzy_matcher_from_list, append_msg
import notes
from logtime import Log
from l import log

def remove_duplicates(items):
    r = []
    for t in all_tasks:
        if t not in r:
            r.append(t)
    return r


l = Log(notes.read('logtime.txt'))
all_tasks = [d.description() for d in l.sorted(lambda i: i.start, reverse=True)]
all_tasks = remove_duplicates(all_tasks)
msg = '+++'
_, typed, selected = select(
    append_msg(
        make_fuzzy_matcher_from_list(all_tasks),
        msg
    )
)

if not selected:
    sys.exit(0)

if selected == msg:
    title = typed
else:
    title = selected

log(title)
