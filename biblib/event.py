import traceback


class Event(list):
    def fire(self, *args, **kargs):
        for handler in self:
            try:
                handler(*args, **kargs)
            except:
                traceback.print_exc()

    def __iadd__(self, other):
        self.append(other)
        return self

    def __isub__(self, other):
        self.remove(other)
        return self

    __call__ = fire
