from abc import abstractmethod, ABC
from pathlib import Path


class ProvidesSeqCount(ABC):
    @abstractmethod
    def next_seq_count(self) -> int:
        pass


class FileSeqCountProvider(ProvidesSeqCount):
    def __init__(self, file_name: Path = "seqcnt.txt"):
        self.file_name = file_name
        if not self.file_name.exists():
            self.create_new()

    def create_new(self):
        with open(self.file_name, "w") as file:
            file.write("0\n")

    def __next__(self):
        if not self.file_name.exists():
            raise FileNotFoundError(f"{self.file_name} file does not exist")
        with open(self.file_name, "r+") as file:
            line = file.readline()
            if not line.isdigit():
                raise ValueError("Sequence count file content is invalid")
            curr_seq_cnt = int(line)
            curr_seq_cnt += 1
            file.seek(0)
            file.write(f"{curr_seq_cnt}\n")
            return curr_seq_cnt
        return -1

    def next_seq_count(self) -> int:
        return self.__next__()
