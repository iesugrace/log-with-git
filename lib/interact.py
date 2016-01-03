def read(prompt):
    import sys
    try:
        print(prompt, end='', file=sys.stderr)
        i = input()
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
    '''
    read a string from the user
    '''
    while True:
        ans = read(prompt)
        if ans:
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
