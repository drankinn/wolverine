import asyncio
import signal

import gunicorn.workers.base as base


class GunicornWorker(base.Worker):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exit_code = 0

    def init_process(self):
        asyncio.get_event_loop().close()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        super().init_process()

    def run(self):
        self._runner = asyncio.ensure_future(self._run(), loop=self.loop)
        self.pulse = asyncio.ensure_future(self.heart_beat(), loop=self.loop)
        self.loop.run_forever()

    async def _run(self):
        self.wsgi.run()

    async def heart_beat(self):
        while self.alive:
            self.notify()
            await asyncio.sleep(self.timeout)

    def init_signals(self):
        pass

