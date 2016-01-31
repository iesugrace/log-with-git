import sys, os
from subprocess import Popen, PIPE
import subprocess
import base64
import string
import re
import time
from record import Record

class InvalidTimeException(Exception): pass
class InvalidReException(Exception): pass
class InvalidCmdException(Exception): pass
class NotTerminalException(Exception): pass

def get_status_byte_output(cmd):
    """ Run the cmd, return the stdout and stderr as
    bytes objects, as well as the stat of the cmd
    (True or False), cmd is a list.
    """
    p       = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr  = p.communicate()
    stat    = p.wait()
    pStat   = (stat == 0)
    res     = (pStat, stdout, stderr)
    return res


def get_status_text_output(cmd):
    """ Run the cmd, return the output as a list of lines
    as well as the stat of the cmd (True or False), content
    of the out will be decoded.
    """
    stat, output = subprocess.getstatusoutput(cmd)
    if stat == 0:
        output = output.split('\n') if output else []
        res    = (True, output)
    else:
        res    = (False, [])
    return res


def isBinary(data):
    """ Deem to be binary data if failed to decode
    """
    try:
        data.decode()
    except UnicodeDecodeError:
        return True
    else:
        return False


def b64encode(iData, lineLen=64):
    """ Take the data which is a bytes,
    encode it with base64, split the resulting
    text into lines of 'lineLen', decode each
    line (it was a bytes) to str, concatenate
    them and return them as a whole long line.
    """
    lineLen = lineLen // 4 * 4  # make it times of 4
    oData   = base64.b64encode(iData)
    res     = []
    while oData:
        line, oData = oData[:lineLen], oData[lineLen:]
        res.append(line.decode())
    return '\n'.join(res)


def b64decode(iData):
    """ Take the str, decode it into binary
    """
    iData = iData.replace('\n', '')
    return base64.b64decode(iData)


def binToAsc(binData):
    """ Convert the binary data into ASCII form
    """
    return b64encode(binData)


class Pager:
    """ Read data from the stdin, write it
    to the stdout using the LESS program
    """
    prog = 'less'
    def __init__(self, args=[]):
        self.pager = Popen([self.prog] + args, stdin=PIPE)

    def write(self, *chunks, isBytes=True):
        for data in chunks:
            if not isBytes:
                data = data.encode()
            self.pager.stdin.write(data)

    def go(self):
        self.pager.stdin.close()
        self.pager.wait()


def makeOneRequest(name, default, datatype, reader, desc):
    """ Create a request entry, used to interactively collect
    information from the user. A request is a dictionary object
    that contains necessary information to interact with the user.
    """
    suffix = (' [%s]: ' % default) if default else ': '
    prompt = desc + suffix
    if reader:
        actual_reader = (lambda prompt, default: reader(prompt, default))
    else:
        actual_reader = reader
    return dict(name=name, prompt=prompt, datatype=datatype,
                default=default, reader=actual_reader)


def pageOut(records):
    """ Apply color to the text, pipe the
    text to a pager, for a better viewing.
    """
    def colorize(record):
        """ Render the first line
        """
        text = str(record)
        if os.isatty(sys.stdout.fileno()):
            pos     = text.find('\n')
            id      = text[:pos]
            cFormat = '\033[0;33m%s\033[0m'
            id      = cFormat % id
            text    = id + text[pos:]
        return text

    if not records:
        return
    lastOne = records.pop()
    pager   = Pager(['-XRF'])
    for record in records:
        pager.write(colorize(record), '\n\n', isBytes=False)
    pager.write(colorize(lastOne), '\n', isBytes=False)
    pager.go()


def validateTime(timeStr):
    """ Check the time string format
    Only check the textual format, not the meaning
    of the time string, therefore 20160230 is valid.
    """
    if timeStr == 'today':
        return True

    lev1_parts = timeStr.split(',')
    for lev1_part in lev1_parts:
        lev2_parts = lev1_part.split(':')
        for x in lev2_parts:
            # empty means 'today'
            regexp = '^(today|-[0-9]+|[0-9]{1,2}|[0-9]{4}|[0-9]{6}|[0-9]{8})?$'
            if re.search(regexp, x) is None:
                return False
    return True


def parsePattern(pstr):
    """ Parse the regular expression pattern

    Valid patterns:
        1. /^DNS.*$/
        2. /home/i          <-- flag
        3. /home/id         <-- multiple flags
        3. scene/home/i     <-- match field 'scene'

    The first punctuation marks the start of the
    pattern, the last same character marks the end
    of the pattern, but they are not part of the
    pattern. A valid pattern must have both two of
    these characters. These is no need to escape
    the same character (the mark) even if there are
    some in the pattern.
    Punctuations: !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~
    """
    flags = {
        'i': re.IGNORECASE,
        'd': re.DOTALL,
        'm': re.MULTILINE,
    }
    punct = '[' + re.escape(string.punctuation) + ']'
    m = re.search(punct, pstr)
    if not m:           # no mark
        raise InvalidReException("invalid pattern: %s" % pstr)
    mark = m.group(0)
    sIdx = pstr.index(mark)
    eIdx = pstr.rindex(mark)
    if sIdx == eIdx:    # only one mark
        raise InvalidReException("invalid pattern: %s" % pstr)
    field   = pstr[:sIdx]
    pattern = pstr[(sIdx+1):eIdx]
    flagStr = pstr[(eIdx+1):]
    flagVal = 0
    for f in flagStr:
        v = flags.get(f)
        if not v:       # unsupported flag
            raise InvalidReException("invalid pattern: %s" % pstr)
        flagVal |= v
    lField = field.lower()
    if lField and lField not in Record.fields:
        raise InvalidReException("no such field: %s" % field)
    return (pattern, flagVal, lField)


def parseTime(timeStr):
    """ Parse the time string, return a list of lists,
    every inner list represents a period of time between
    two points, the relationship between all inner lists
    is OR, not AND.
    """
    if timeStr == 'today':
        return [todayPeriod()]

    allPairs   = []
    lev1_parts = timeStr.split(',')
    for lev1_part in lev1_parts:
        lev2_parts = lev1_part.split(':')
        if len(lev2_parts) == 2: # start time and end time
            firstSecond, junk = compreTime(lev2_parts[0])
            junk, lastSecond  = compreTime(lev2_parts[1])
            allPairs.append([firstSecond, lastSecond])
        else:   # one time
            pair = compreTime(lev2_parts[0])
            allPairs.append(pair)
    return allPairs


def todayPeriod():
    """ Return the first and the last seconds of today
    """
    return dayPeriod()


def dayPeriod(ts=None):
    """ Return the first and the last seconds
    of a day, 'ts' is a time.struct_time object,
    if omitted, assume the current time.
    """
    if ts is None:
        ts = time.localtime()
    ts1 = time.strptime('%d%02d%02d' % ts[:3], '%Y%m%d')
    firstSecond = int(time.mktime(ts1))
    timeStr = '%d%02d%02d%02d%02d%02d' % (ts[:3] + (23, 59, 59))
    ts2 = time.strptime(timeStr, '%Y%m%d%H%M%S')
    lastSecond  = int(time.mktime(ts2))
    return [firstSecond, lastSecond]


def compreTime(text):
    """ Distinguish between year and other
    time format, call compreYear and compreDay
    accordingly. Empty string means 'today'.
    """
    if not text:
        return todayPeriod()
    if len(text) == 4 and text[:2] == '20':
        return compreYear(text)
    else:
        return compreDay(text)


def compreYear(text):
    """ Take the given number string as a year, return
    the first second and the last second of the year.
    """
    firstDay = time.strptime(text, '%Y')
    lastDay  = time.strptime('%s%s%s' % (text, '12', '31'), '%Y%m%d')
    firstSecond, junk = dayPeriod(firstDay)
    junk, lastSecond  = dayPeriod(lastDay)
    return [firstSecond, lastSecond]


def compreDay(text):
    """ Parse the given number string, return the
    first second and the last second of the day.
    """
    l = len(text)

    try:
        if text[0] == '-':          # negative day
            days = int(text)
            second = time.time() + 86400 * days
            res = time.localtime(second)
        elif 1 <= l <= 2:           # a day of the current month
            y, m = time.localtime()[:2]
            d = int(text)
            res = time.strptime('%s%02d%02d' % (y, m, d), '%Y%m%d')
        elif l == 4:                # day of a specific month
            y = time.localtime()[0]
            res = time.strptime('%s%s' % (y, text), '%Y%m%d')
        elif l == 6:                # month of a specific year
            res = time.strptime(text, '%Y%m')
        elif l == 8:                # a day of a month of a year
            res = time.strptime(text, '%Y%m%d')
    except:
        raise InvalidTimeException("invalid time: %s" % text)
    return dayPeriod(res)
