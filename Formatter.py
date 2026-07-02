from pprint import PrettyPrinter

class FormatPrinter(PrettyPrinter):
    def __init__(self, formats, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.formats = formats

    def format(self, obj, ctx, maxlvl, lvl):
        if type(obj) in self.formats:
            fmt = self.formats[type(obj)]
            if callable(fmt):
                return fmt(obj), 1, 0
            # else assume format string
            return fmt.format(obj), 1, 0
        return PrettyPrinter.format(self, obj, ctx, maxlvl, lvl)

