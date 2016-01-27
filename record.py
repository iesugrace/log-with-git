import os
from  timeutils import isodatetime, strtosecond

class BasicRecord:
    """ Define the basic methods of a record

    Sub-classes shall define the fields, and
    a __repr__ method.
    """
    def __init__(self, **fields):
        """ We don't do any validation or convertion
        on the fields here. The input data 'fields'
        shall be set properly according to the field
        definition of the sub-class.
        """
        for k, v in fields.items():
            setattr(self, k, v)

    def elements(self):
        """ Return a dictionary containing
        all elements of the record
        """
        return self.__dict__

    def __eq__(self, record):
        """ compare with another record
        """
        if not isinstance(record, Record):
            return False
        for name in self.fields:
            if getattr(self, name) != getattr(record, name):
                return False
        return True

    def __ne__(self, record):
        """ compare with another record, if are not equal
        """
        return not self.__eq__(record)


class Record(BasicRecord):
    """ Define the fields and other methods
    """
    # Definition of fields of the Log record
    # no 'required' field means not required
    # no 'conv' field means default to str
    # the first conv for writing to file
    # the second conv for loading from file
    fields = {
        'subject': {'required': True, 'order': 1},
        'author':  {'required': True, 'order': 2},
        'time':    {'required': True, 'order': 3,
                    'conv': [isodatetime, strtosecond]},
        'scene':   {'order': 4},
        'people':  {'order': 5},
        'tag':     {'order': 6},
        'data':    {'order': 7},
        'binary':  {'conv': [(lambda v: ['false', 'true'][bool(v)]),
                            (lambda s: s == 'true')], 'order': 8},
    }

    sep = ':'  # separator between key and value

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
        values = [self.author, isodatetime(self.time),
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
