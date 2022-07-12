from .test_src_handler import TestCfdpSourceHandler


class TestCfdpSourceHandlerWithClosure(TestCfdpSourceHandler):
    def setUp(self) -> None:
        self.common_setup(True)

    def test_empty_file(self):
        self._common_empty_file_test()

    def test_small_file(self):
        pass
