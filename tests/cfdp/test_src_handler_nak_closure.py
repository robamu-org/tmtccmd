from .test_src_handler import TestCfdpSourceHandler


class TestCfdpSourceHandlerWithClosure(TestCfdpSourceHandler):

    def setUp(self) -> None:
        self.common_setup(True)
