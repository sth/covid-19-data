class FileColumns(object):
    def __init__(self, indexes, types):
        self.indexes = indexes
        self.types = types
        class Columns(object):
            __slots__ = list(indexes.keys())
        self.Columns = Columns

    def get(self, line):
        cl = self.Columns()
        for field, idx in self.indexes.items():
            if idx is None:
                setattr(cl, field, None)
            else:
                value = line[idx]
                if field in self.types:
                    value = self.types[field](value)
                setattr(cl, field, value)
        return cl

class CSVColumns(object):
    def __init__(self, **fields):
        self.fields = fields
        self.types = {}
        self.current = None

    def set_type(self, field, parser):
        self.types[field] = parser

    def set_types(self, **kw):
        for field, parser in kw.items():
            self.set_type(field, parser)

    def build(self, fileheader):
        indexes = {}
        for field, headers in self.fields.items():
            if not isinstance(headers, (list, tuple)):
                headers = [headers]
            for header in headers:
                if header is None:
                    indexes[field] = None
                    break
                try:
                    indexes[field] = fileheader.index(header)
                    break
                except ValueError as e:
                    continue
            else:
                raise KeyError('No column found for field %r in %r' % (field, fileheader))
        return FileColumns(indexes, self.types)
