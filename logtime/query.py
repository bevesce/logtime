import re
from datetime import datetime




def parse(query_string):
    query_string = transform_datetimes(query_string)

    def query(logitem):
        values = {
            'start': logitem.start,
            'end': logitem.end,
            'tags': logitem.tags,
            'duration': logitem.get_duration(),
            'description': logitem.get_description(),
            'datetime': datetime,
            'd': datetime,
        }
        try:
            return eval(query_string, values)
        except:
            return False
    return query


def transform_datetimes(query_string):
    datetime_pattern = re.compile('(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d)')
    date_pattern = re.compile('(\d\d\d\d)-(\d\d)-(\d\d)')
    query_string = datetime_pattern.sub(transform_datetime, query_string)
    query_string = date_pattern.sub(transform_datetime, query_string)
    return query_string


def transform_datetime(match):
    return 'datetime({})'.format(', '.join(v.lstrip('0') for v in match.groups()))
