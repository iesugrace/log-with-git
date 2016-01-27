from logrecord import LogRecord
import timeutils

class XmlStorage:
    """ XML storage engine for the record
    """
    @staticmethod
    def sourceToDom(code):
        """ Parse the raw record data which is XML code,
        return a Xml DOM object.
        """
        from xml.dom.minidom import parseString
        return parseString(code)

    @staticmethod
    def load(path):
        """ Load the content of the path,
        parse it, and return a record instance.
        """
        try:
            code = open(path).read()
            doc  = XmlStorage.sourceToDom(code)
        except:
            return None

        # collect all fields' data
        fields = {}
        for node in doc.firstChild.childNodes:
            if node.nodeType == node.ELEMENT_NODE:
                name = node.localName
                textNode = node.firstChild
                data = textNode.data if textNode else ''
                desc = LogRecord.fields.get(name)
                if not desc:    # ignore any fields not defined
                    continue
                conv = desc.get('conv', [str, str])[1]
                fields[name] = conv(data)
        fields['path'] = path   # this field is not set in the file
        return LogRecord(**fields)

    @staticmethod
    def createNode(root, nodeName, nodeText):
        """ Add an element node with nodeText to the 'root' element
        """
        from xml.dom.minidom import Element, Text
        ele = Element(nodeName)
        text = Text()
        text.data = nodeText
        ele.appendChild(text)
        root.appendChild(ele)

    @staticmethod
    def recordToSource(record):
        """ Compose Xml source code from a record object
        """
        from xml.dom.minidom import Document, Text
        import re
        doc  = Document()
        root = doc.createElement("log")
        doc.appendChild(root)
        items = sorted(LogRecord.fields.items(),
                    key=(lambda x: x[1]['order']))
        for name, desc in items:
            conv  = desc.get('conv', [str, str])[0]
            value = conv(getattr(record, name))
            XmlStorage.createNode(root, name, value)
        xmlCode = doc.toprettyxml()
        xmlCode = re.sub('\t', ' ' * 4, xmlCode)    # replace tabs with spaces
        return xmlCode

    @staticmethod
    def save(record, path):
        """ Convert the record to Xml code,
        and Write the code to the path.
        """
        code = XmlStorage.recordToSource(record)
        open(path, 'w').write(code)
