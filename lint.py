#!/usr/bin/env python3
import os
import sys


def main():
    # Ignore folder created by venv
    exclude_dirs_flag = '--exclude bin,lib'
    additional_flags_both_steps = '--count --statistics'
    additional_flags_first_step = '--select=E9,F63,F7,F82 --show-source'
    flake8_first_step_cmd = \
        f'flake8 . {additional_flags_both_steps} {additional_flags_first_step} {exclude_dirs_flag}'
    status = os.system(flake8_first_step_cmd)
    if os.WEXITSTATUS(status) != 0:
        print("Flake8 linter errors")
        sys.exit(0)
    flake8_second_step_cmd = \
        f'flake8 . {additional_flags_both_steps} --exit-zero --max-complexity=10 ' \
        f'--max-line-length=127 {exclude_dirs_flag}'
    os.system(flake8_second_step_cmd)


if __name__ == "__main__":
    main()
