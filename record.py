import os
import timeutils

class Record:
    """ Define the fields and methods of a record
    Fields and types:
    subject  --  str
    author   --  str
    time     --  int
    scene    --  str
    people   --  str
    tag      --  str
    data     --  str (maybe base64 text for binary data)
    """
    sep = ':'  # separator between key and value

    def __init__(self, subject, author, time=None, scene='',
                        people='', tag='', data='', path=None):
        time = time if time else timeutils.isodatetime()
        self.subject   =  subject
        self.author    =  author
        self.time      =  timeutils.strtosecond(time)
        self.scene     =  scene
        self.people    =  people
        self.tag       =  tag
        self.data      =  data
        self.path      =  path

    def __repr__(self):
        text = '%s\n\n%s' % (self.__header(), self.subject)
        if self.binary:
            data = "-->> Binary data <<--"
        else:
            data = self.data
        if data:
            text = '%s\n\n%s' % (text, data.rstrip('\n'))
        return text

    def __header(self):
        """ Construct the header of the Log
        Return a str object, no ending new-line.
        """
        keys   = ['Author', 'Time', 'Scene', 'People', 'Tag']
        keys   = [x + self.sep for x in keys]   # append the separator
        values = [self.author, timeutils.isodatetime(self.time),
                        self.scene, self.people, self.tag]
        maxlen = max([len(x) for x in keys])
        fmt    = '%%-%ds %%s\n' % maxlen
        text   = ''
        for k, v in zip(keys, values):
            if v:
                text += fmt % (k, v)
        id     = os.path.basename(self.path) if self.path else 'N/A'
        text   = 'log %s\n%s' % (id, text[:-1])
        return text     # remove the last new-line

    def elements(self):
        """ Return a dictionary containing
        all elements of the record
        """
        return self.__dict__
