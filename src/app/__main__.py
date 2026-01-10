"""Module entrypoint for `python -m src.app`."""

import sys

from src.system import preload_cuda_libs
from src.app import run_app


def main():
    preload_cuda_libs()
    sys.exit(run_app())


if __name__ == "__main__":
    main()
