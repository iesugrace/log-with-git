import os

class Config:
    """ Process and store the user settings

    Subclass can redefine the attribute 'fileName'
    and the method 'validate' to suite the needs.
    """

    fileName = '.logrc'

    def __init__(self, path=None):
        if not path:
            path = os.path.join(os.getenv('HOME'), self.fileName)
        code       = open(path).read()
        configs    = {}
        exec(code, configs)
        configs    = {k: v for k, v in configs.items() if k[0] != '_'}
        self.data  = configs

    def validate(self):
        """ Validate the config items
        
        Rule for the dataDir:
        1. exists and is a directory, or
        2. not yet exists
        """
        configs    = self.data
        dataDir    = configs.get('dataDir')
        dataDirSet = False
        if dataDir and (
            os.path.isdir(dataDir) or
            not os.path.exists(dataDir)):
                dataDirSet = True
        assert dataDirSet, "config: no appropriate data directory"
        assert configs.get('authorName'), "config: author name not set"
        assert configs.get('authorEmail'), "config: author email not set"
