from selector import sel, make_fmatcher
import logtime

all_tasks = {t.title for t in logtime.Calendar.from_file(logtime.logtime_path).all_tasks()}

r = sel(make_fmatcher(all_tasks))
if r:
    _, _, title = r
    logtime.start_task(title)
    logtime.summarize()
