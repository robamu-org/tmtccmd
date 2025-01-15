from __future__ import annotations


class FileInfo:
    def __init__(
        self,
        file_name: str,
        repo_path: str,
        file_size: int = 0,
        lock_status: bool = False,
    ):
        self.file_name = file_name
        self.repo_path = repo_path
        self.file_size = file_size
        self.lock_status = lock_status
