import argparse
import asyncio
from enum import Enum

from .app import App


class Command(str, Enum):
    REFRESH = "refresh"
    EXPORT = "export"


async def main():
    parser = argparse.ArgumentParser("djlib", description="DJ library management")
    parser.add_argument(
        "command", choices=[command.value for command in Command], help="Command"
    )
    args = parser.parse_args()

    async with App() as app:
        command = Command(args.command)
        match command:
            case Command.REFRESH:
                await app.refresh()
            case Command.EXPORT:
                await app.update(app.spotify, app.rekordbox)


if __name__ == "__main__":
    asyncio.run(main())
