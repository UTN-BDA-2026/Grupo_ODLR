"""
Entry point for running migrations via: python -m migrations
"""

import asyncio
import sys

from migrations.cli import main

if __name__ == "__main__":
    asyncio.run(main())
