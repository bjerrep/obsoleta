#!/usr/bin/env python3
from test_common import title, test_success
from dixi_api import DixiApi
from common import Param
from log import logger
import logging


my_root = 'testdata/G2_test_slot'

logger.setLevel(logging.INFO)

param = Param()
param.set_depth(2)
param.set_root(my_root)

dixi = DixiApi('testdata/test.conf', param)

# get_compact

title('TDA_1A', 'get_compact')
success, messages = dixi.get_compact('testdata/G2_test_slot/a')
test_success(success, messages)
