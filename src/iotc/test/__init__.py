async def empty_fn():
    pass


async def stop():
    import asyncio
    for task in asyncio.all_tasks():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class dummy_storage:
    def retrieve(self):
        return {}

    def persist(self, credentials):
        return None
