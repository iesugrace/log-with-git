# import the readline module to give editing
# support for the input function.

import readline
import re


def read(prompt):
    import sys
    try:
        i = input(prompt)
        return i
    except (KeyboardInterrupt, EOFError):
        print()
        exit()

def readint(prompt='', default=None):
    '''
    read an integer from the user
    '''
    while True:
        ans = read(prompt)
        if ans:
            if ans.isdigit():
                return int(ans)
        elif default is not None:
            return default
        print('invalid input')

def readstr(prompt='', default=None):
    """ Read a string from the user

    When the input starts with a plus sign '+',
    add it to the default if default is provided,
    separated by SEP.

    When the input starts with a minus sign '-',
    remove it from the default if default is provided,
    separator is SEP.

    When the input starts with double minus sign '--',
    return an empty string.
    """

    # add the Chinese comma as separator,
    # use re for splitting.
    SEP  = '[,，]'
    JSEP = ', '
    def cleanSplit(text):
        """ Split by SEP, strip white spaces
        at the left and the right, return a list.
        """
        if text:
            xs = re.split('[,，]', text)
            #xs = text.split(SEP)
            xs = [x.strip() for x in xs]
        else:
            xs = []
        return xs

    while True:
        ans = read(prompt)
        if ans:
            if ans[:2] == '--':
                ans = ''
            elif ans[0] == '-':
                oldElements = cleanSplit(default)
                newElements = cleanSplit(ans[1:])
                resElements = [x for x in oldElements if x not in newElements]
                ans = JSEP.join(resElements)
            elif ans[0] == '+':
                oldElements = cleanSplit(default)
                newElements = cleanSplit(ans[1:])
                resElements = oldElements + newElements
                ans = JSEP.join(resElements)
            else:
                resElements = cleanSplit(ans)
                ans = JSEP.join(resElements)
            return ans
        elif default is not None:
            return default
        print('invalid input')

def printAndPick(data, lineMode=False, default=None, prompt='pick one by number: '):
    '''
    print the items in the data, then pick one,
    the items in the data shall overload the
    __str__ or __repr__ for printing as string
    '''
    count = len(data)
    for number, item in enumerate(data, 1):
        if lineMode:
            print('%s. ' % number, end='')
        else:
            print('-- %s ' % number + '-' * 50)
        print(item)

    return pick(data, default=default, prompt=prompt)

def pick(data, default=None, prompt='pick one by number: '):
    '''
    pick one item from the 'data' by number
    '''
    count = len(data)
    while True:
        number = readint(prompt, default=default)
        if number == -1:                # allow user to just press Enter
            return None, None           # without input anything

        if number >= 1 and number <= count:
            index = number - 1
            return index, data[index]
        else:
            print('number out of range')

def pickInRange(start=0, end=None, prompt='pick one by number: '):
    data = list(range(start, end))
    index, item = pick(data, prompt=prompt)
    return index

def readMany(requests):
    """
    read data from user interactively, data read from the
    user may be of int or str, default values may be supplied.
    if 'reader' is not supplied, readint or readstr will be used
    depends on the 'type'.
    the format of the requests:
    [
        dict(name='stime', prompt='start time: ',    datatype=str, default=None, reader=None),
    ]

    returns a directory of this format:
    {
        'age': 20,
        'sex': 'Female',
    }
    """
    def setReader(valtype, default):
        if default:
            reader = default
        else:
            if valtype == int:
                reader = readint
            elif valtype == str:
                reader = readstr
            else:
                raise 'type %s is not supported' % str(ent['type'])
        return reader

    res = {}
    for ent in requests:
        key     = ent['name']
        prompt  = ent['prompt']
        reader  = ent['reader']
        valtype = ent['datatype']
        default = ent['default']
        reader  = setReader(valtype, reader)
        v       = reader(prompt, default=default)
        res[key] = v

    return res
