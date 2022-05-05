# -*- coding: utf-8 -*-
import enum


class Subservices(enum.IntEnum):
    TM_ACCEPTANCE_SUCCESS = 1
    TM_ACCEPTANCE_FAILURE = 2
    TM_START_SUCCESS = 3
    TM_START_FAILURE = 4
    TM_STEP_SUCCESS = 5
    TM_STEP_FAILURE = 6
    TM_COMPLETION_SUCCESS = 7
    TM_COMPLETION_FAILURE = 8
