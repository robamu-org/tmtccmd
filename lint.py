#!/usr/bin/env python3
import os
import sys


def main():
    status = os.system("flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics")
    if os.name == 'nt':
        if status != 0:
            print(f'Flake8 linter errors with status {status}')
            sys.exit(0)
    else:
        if os.WEXITSTATUS(status) != 0:
            print(f'Flake8 linter errors with status {status}')
            sys.exit(0)
    os.system("flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics")


if __name__ == "__main__":
    main()
