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
        if not isinstance(record, BasicRecord):
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
    # the first conv:  --> Record
    # the second conv:     Record -->
    fields = {
        'id':      {'order': 1},    # id is engine dependent
        'subject': {'required': True, 'order': 2},
        'author':  {'required': True, 'order': 3},
        'time':    {'required': True, 'order': 4,
                    'conv': [strtosecond, isodatetime]},
        'scene':   {'order': 5},
        'people':  {'order': 6},
        'tag':     {'order': 7},
        'data':    {'order': 8},
        'binary':  {'order': 9, 'conv': [(lambda s: s == 'true'),
                         (lambda v: ['false', 'true'][bool(v)])]},
    }

    sep = ':'  # separator between key and value

    def __repr__(self):
        """ Class specific representation method
        Subclass shall redefine this method.
        """
        keys   = ['Author', 'Time', 'Scene', 'People', 'Tag']
        c      = lambda x: x
        cvtMap = zip(keys, [c, isodatetime] + [c] * 6)
        values = [c(getattr(self, k.lower())) for k, c in cvtMap]
        keys   = [x + self.sep for x in keys]   # append the separator
        maxlen = max([len(x) for x in keys])
        fmt    = '%%-%ds %%s\n' % maxlen
        text   = ''
        for k, v in zip(keys, values):
            if v:
                text += fmt % (k, v)
        id     = self.id if self.id else 'N/A'
        text   = 'log %s\n%s' % (id, text[:-1])
        text   = '%s\n\n%s' % (text, self.subject)
        if self.binary:
            data = "-->> Binary data <<--"
        else:
            data = self.data
        if data:
            text = '%s\n\n%s' % (text, data.rstrip('\n'))
        return text

    def save(self, oldRecord=None):
        """ Instance data persistent method
        """
        return Record.engine.save(self, oldRecord)

    @staticmethod
    def load(id):
        return Record.engine.load(id)

    @staticmethod
    def allIds():
        return Record.engine.allIds()

    @staticmethod
    def matchId(id):
        return Record.engine.matchId(id)

    @staticmethod
    def fieldDef(name):
        """ Return the field definition
        """
        return Record.fields[name]

    @staticmethod
    def getConv(name, toRecord=True):
        """ Return the converter of a field
        """
        idx = 0 if toRecord else 1
        return Record.fields[name]['conv'][idx]
