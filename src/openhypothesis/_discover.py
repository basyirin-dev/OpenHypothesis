from typing import Self


class Discover:
    def __init__(self: Self, question: str) -> None:
        self.question = question

    async def execute(self: Self) -> None:
        raise NotImplementedError
