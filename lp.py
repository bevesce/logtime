import sys

from selector import select, make_fuzzy_matcher_from_list, append_msg
import logtime

all_tasks = {
    t.title for t in logtime.Calendar.from_file(logtime.logtime_path).all_tasks()
}
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

logtime.start_task(title)
logtime.summarize()
