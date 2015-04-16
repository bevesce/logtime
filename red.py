import logtime
import re
import colors
import config
from redmine import Redmine

redmine = Redmine(
    config.redmine_url, username=config.redmine_username, password=config.redmine_password
)


def make_mnemonic(text):
    text = text.lower()
    splited = text.split(' ')
    if len(splited) == 1:
        return text[:2]
    return ''.join([w[:1] for w in splited])

redmine_activities_mnemonics = {
    make_mnemonic(k): v for k, v in config.redmine_activities.iteritems()
}


class RedmineEntry(object):
    def __init__(self, title, duration):
        self.hours = duration.total_seconds() / 3600
        self.description = title
        self.issue_id = self.get_issue_id(title)
        self.activity_id = self.get_activity_id(title)

    def get_issue_id(self, title):
        f = re.findall(r'#(\d+)', title)
        if f:
            return int(f[-1])
        return self.ask_for_id()

    def get_activity_id(self, title):
        f = re.findall(r'@(\w+)', title)
        activity_mnemonic = None
        if f:
            activity_mnemonic = f[-1]
        return redmine_activities_mnemonics.get(
            activity_mnemonic,
            config.redmine_default_activity_id
        )

    def ask_for_id(self):
        print colors.gray('issue id for:'), self.description
        return int(raw_input())

    def push(self):
        print self.description, self.activity_id, self.issue_id, self.hours
        # redmine.time_entry.create(
        #     issue_id=self.issue_id, hours=self.hours, activity_id=self.activity_id, comments=self.description[:255]
        # )
        print '{:.03f} {} {}#{} {}{}'.format(
            self.hours, self.description, colors.GRAY, self.issue_id, self.activity_id, colors.DEFC
        )


day = logtime.Calendar.from_file(logtime.logtime_path).get_day(
    logtime.CalendarKey.now()
)
for task in day.iter_tasks():
    if task.is_break:
        continue
    RedmineEntry(task.title, task.duration).push()
