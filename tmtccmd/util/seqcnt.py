from abc import abstractmethod, ABC
from pathlib import Path


class ProvidesSeqCount(ABC):
    @property
    @abstractmethod
    def max_bit_width(self) -> int:
        pass

    @max_bit_width.setter
    @abstractmethod
    def max_bit_width(self, width: int):
        pass

    @abstractmethod
    def next_seq_count(self) -> int:
        """Contract: Retrieve the current sequence count and then increment it"""
        raise NotImplementedError(
            "Please use a concrete class implementing this method"
        )

    def __next__(self):
        return self.next_seq_count()


class FileSeqCountProvider(ProvidesSeqCount):
    def __init__(self, max_bit_width: int, file_name: Path = Path("seqcnt.txt")):
        self.file_name = file_name
        self._max_bit_width = max_bit_width
        if not self.file_name.exists():
            self.create_new()

    @property
    def max_bit_width(self) -> int:
        return self._max_bit_width

    @max_bit_width.setter
    def max_bit_width(self, width: int):
        self._max_bit_width = width

    def create_new(self):
        with open(self.file_name, "w") as file:
            file.write("0\n")

    def current(self) -> int:
        if not self.file_name.exists():
            raise FileNotFoundError(f"{self.file_name} file does not exist")
        with open(self.file_name) as file:
            return self.check_count(file.readline())

    def next_seq_count(self) -> int:
        if not self.file_name.exists():
            raise FileNotFoundError(f"{self.file_name} file does not exist")
        with open(self.file_name, "r+") as file:
            curr_seq_cnt = self.increment_with_rollover(
                self.check_count(file.readline())
            )
            file.seek(0)
            file.write(f"{curr_seq_cnt}\n")
            return curr_seq_cnt

    def check_count(self, line: str) -> int:
        line = line.rstrip()
        if not line.isdigit():
            raise ValueError("Sequence count file content is invalid")
        curr_seq_cnt = int(line)
        if curr_seq_cnt < 0 or curr_seq_cnt > pow(2, self.max_bit_width) - 1:
            raise ValueError("Sequence count in file has invalid value")
        return curr_seq_cnt

    def increment_with_rollover(self, seq_cnt: int) -> int:
        """CCSDS Sequence count has maximum size of 14 bit. Rollover after that size by default"""
        if seq_cnt >= pow(2, self.max_bit_width) - 1:
            return 0
        else:
            return seq_cnt + 1


class PusFileSeqCountProvider(FileSeqCountProvider):
    def __init__(self, file_name: Path = Path("seqcnt.txt")):
        super().__init__(max_bit_width=14, file_name=file_name)
