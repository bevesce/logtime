from datetime import datetime
from logtime import DATETIME_FORMAT
import notes


def log(tags=''):
    notes.append(
        'logtime.txt',
        '{}\n{}'.format(
            datetime.now().strftime(DATETIME_FORMAT),
            tags
        )
    )


if __name__ == '__main__':
    import sys
    log(' '.join(sys.argv[1:]))
