class Logger:
    debug: bool

    def set_debug(self, debug: bool):
        self.debug = debug

    def output(self, *args):
        if not self.debug:
            return

        print(f'DEBUG [{self.datetime}]:', *args)

    @property
    def datetime(self) -> str:
        import utime

        tm = utime.localtime()

        return f'{tm[0]:04}-{tm[1]:02}-{tm[2]:02} {tm[3]:02}:{tm[4]:02}:{tm[5]:02}'

logger = Logger()
