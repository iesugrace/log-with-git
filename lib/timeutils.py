from time import *

def isotime(second=None):
    """ Make a time string
    """
    if not second: second = time.time()
    return strftime('%H:%M:%S', localtime(second))


def isodate(second=None):
    """ Make a date string
    """
    if not second: second = time.time()
    return strftime('%Y-%m-%d', localtime(second))


def isodatetime(second=None):
    """ Make a string of date and time
    """
    if not second: second = time()
    return strftime('%Y-%m-%d %H:%M:%S', localtime(second))


def isostrtosecond(timestr):
    """ Convert a date time string to an integer value of second
    """
    return int(mktime(strptime(timestr, '%Y-%m-%d %H:%M:%S')))


def strtosecond(timestr):
    """ Conert various format of time string to second
    Valid formats of time string:
        14:09
        14:09:01
        2015-06-15
        2015-06-15 14:09
        2015-06-15 14:09:01
    """
    # this function adds the 'second' part if omitted
    def complete_time(timestr):
        if len(timestr.split(':')) == 2:
            timestr += ':00'
        return timestr

    arr = timestr.split(' ')
    arr[-1] = complete_time(arr[-1])

    # only date or time is supplied, but not both
    if len(arr) == 1:
        if '-' in timestr:  # it is a date string
            arr.append('00:00:00')
        else:               # it is a time string, prepend the current date
            arr.insert(0, strftime('%Y-%m-%d'))

    timestr = ' '.join(arr)
    return isostrtosecond(timestr)
