# logtime

simple script to log tasks

![logtime](http://procrastinationlog.net/images/logtime.png)

Log and show time spent on tasks.
Using without argument will show logged tasks with time spent on them.
Using with some text will start new task.
Prepend task description with *@* to mark it as a break.
Prepend task description with *#* to mark it as a comment.

Usage:
* `logtime.py <task_description>...`
* `logtime.py -e`
* `logtime.py -f`
* `logtime.py`

Options:
* `-h --help`                     Show this screen.
* `-e --end`                      End current task.
* `-f --file`                     Open file with log.