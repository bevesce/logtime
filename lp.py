from selector import sel, make_fmatcher, append_msg
import logtime

all_tasks = {t.title for t in logtime.Calendar.from_file(logtime.logtime_path).all_tasks()}
msg = '+++'
r = sel(
    append_msg(
        make_fmatcher(all_tasks),
        msg
    )
)

if r:
    _, typed, selected = r
    if selected == msg:
        title = typed
    else:
        title = selected
    logtime.start_task(title)
    logtime.summarize()
