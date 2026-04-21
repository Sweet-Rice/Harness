class EventEmitter:
    def __init__(self, on_event=None):
        self._on_event = on_event

    async def emit(self, event_type: str, content: str):
        if self._on_event:
            await self._on_event(event_type, content)

    async def stream_start(self):
        await self.emit("stream_start", "")

    async def stream_token(self, token: str):
        await self.emit("stream_token", token)

    async def stream_thinking(self, token: str):
        await self.emit("stream_thinking", token)

    async def stream_end(self):
        await self.emit("stream_end", "")

    async def log(self, content: str):
        await self.emit("log", content)

    async def message(self, content: str):
        await self.emit("message", content)
