import notes
from logtime import Log

l = Log(notes.read('logtime.txt'))

print(l.filter(lambda i: 'symbolay 2.0' in i.tags))
print(l.filter(lambda i: 'symbolay 2.0' in i.tags).sum())
print(l
    .filter(lambda i: 'symbolay 2.0' in i.tags)
    .group(lambda i: i.start.year)
    .sum()
)