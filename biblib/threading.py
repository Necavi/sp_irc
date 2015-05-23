from threading import Thread as _Thread
from listeners import tick_listener_manager


class Thread(_Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tick_listener_manager.register_listener(self._tick)

    def _tick(self):
        pass