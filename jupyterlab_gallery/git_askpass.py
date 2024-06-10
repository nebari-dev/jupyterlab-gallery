#!/usr/bin/env python

import os
import sys

what = sys.argv[1].lower()

if "username" in what:
    print(os.environ["GIT_PULLER_ACCOUNT"])
if "password" in what:
    print(os.environ["GIT_PULLER_TOKEN"])
