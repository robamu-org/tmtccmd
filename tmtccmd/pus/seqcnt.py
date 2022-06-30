from abc import abstractmethod, ABC
from pathlib import Path


class ProvidesSeqCount(ABC):
    @abstractmethod
    def next_seq_count(self) -> int:
        raise NotImplementedError(
            "Please use a concrete class implementing this method"
        )


class FileSeqCountProvider(ProvidesSeqCount):
    def __init__(self, file_name: Path = Path("seqcnt.txt")):
        self.file_name = file_name
        if not self.file_name.exists():
            self.create_new()

    def create_new(self):
        with open(self.file_name, "w") as file:
            file.write("0\n")

    def current(self) -> int:
        if not self.file_name.exists():
            raise FileNotFoundError(f"{self.file_name} file does not exist")
        with open(self.file_name) as file:
            return self.check_count(file.readline())

    def __next__(self):
        if not self.file_name.exists():
            raise FileNotFoundError(f"{self.file_name} file does not exist")
        with open(self.file_name, "r+") as file:
            curr_seq_cnt = self.increment_with_rollover(
                self.check_count(file.readline())
            )
            file.seek(0)
            file.write(f"{curr_seq_cnt}\n")
            return curr_seq_cnt

    @staticmethod
    def check_count(line: str) -> int:
        line = line.rstrip()
        if not line.isdigit():
            raise ValueError("Sequence count file content is invalid")
        curr_seq_cnt = int(line)
        if curr_seq_cnt < 0 or curr_seq_cnt > pow(2, 14) - 1:
            raise ValueError("Sequence count in file has invalid value")
        return curr_seq_cnt

    def next_seq_count(self) -> int:
        return self.__next__()

    @staticmethod
    def increment_with_rollover(seq_cnt: int) -> int:
        """CCSDS Sequence count has maximum size of 14 bit. Rollover after that size by default"""
        if seq_cnt >= pow(2, 14) - 1:
            return 0
        else:
            return seq_cnt + 1
