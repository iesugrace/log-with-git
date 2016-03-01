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
        'mtime':   {'required': True, 'order': 5,
                    'conv': [strtosecond, isodatetime]},
        'scene':   {'order': 6},
        'people':  {'order': 7},
        'tag':     {'order': 8},
        'data':    {'order': 9},
        'binary':  {'order': 10, 'conv': [(lambda s: s == 'true'),
                         (lambda v: ['false', 'true'][bool(v)])]},
    }
    sep = ':'  # separator between key and value

    def __repr__(self):
        data = self.elements()
        return Record.defaultFormater(data)

    @staticmethod
    def defaultFormater(data, colorFunc, n=1):
        """ 'n' parameter controls the number
        of newline characters to prepend, colorFunc
        apply color to the text.
        """
        keys  = ['Author', 'Time', 'MTime', 'Scene', 'People', 'Tag']
        conv  = lambda x: x
        funcs = [conv, isodatetime, isodatetime] + [conv] * 6
        text  = colorFunc(Record.formatRecord(keys, funcs, data))
        return  ''.join(['\n'] * n) + text + '\n'

    @staticmethod
    def formatRecord(keys, funcs, data):
        """ Class specific representation method
        Subclass shall redefine the methods called
        by this method.
        """
        text = Record.formatFields(keys, funcs, data)
        text = Record.formatPrependId(text, data)
        text = Record.formatAppendSubject(text, data)
        text = Record.formatAppendData(text, data)
        return text

    @staticmethod
    def formatAppendData(text, data):
        if data.get('binary', False):
            x = "-->> Binary data <<--"
        else:
            x = data.get('data', '')
        if x:
            text = '%s\n\n%s' % (text, x.rstrip('\n'))
        return text

    @staticmethod
    def formatAppendSubject(text, data):
        """ Append subject to the text
        """
        return '%s\n\n%s' % (text, data.get('subject', ''))

    @staticmethod
    def formatPrependId(text, data):
        """ Prepend ID to the text
        """
        id = data.get('id', 'N/A')
        return 'log %s\n%s' % (id, text)

    @staticmethod
    def formatFields(keys, funcs, data):
        """ Format a text string of the fields
        keys is the fields' names.
        """
        cvtMap = zip(keys, funcs)
        values = [c(data.get(k.lower())) for k, c in cvtMap]
        keys   = [x + Record.sep for x in keys]   # append the separator
        maxlen = max([len(x) for x in keys])
        fmt    = '%%-%ds %%s\n' % maxlen
        text   = ''
        for k, v in zip(keys, values):
            if v:
                text += fmt % (k, v)
        return text[:-1]

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

    @staticmethod
    def convertFields(items, toRecord=True):
        """ Make the data in items suitable for creating a
        record instance if toRecord is True, else do a
        reverse conversion. items is an iterable that has
        key/value items, the key is the name of the field,
        the value is the data to convert.  Default converter
        is 'str'.
        """
        res = {}
        idx = 0 if toRecord else 1
        for k, v in items:
            desc = Record.fields.get(k)
            if not desc:    # ignore any fields not defined
                continue
            conv = desc.get('conv', [str, str])[idx]
            res[k] = conv(v)
        return res
