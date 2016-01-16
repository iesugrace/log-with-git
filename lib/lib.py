from subprocess import Popen, PIPE
import base64

class InvalidTimeException(Exception): pass
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
