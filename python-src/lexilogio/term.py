#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr  8 23:41:57 2023

@author: mathaes
"""


class Term:
    def __init__(self):
        self.pkey = -1
        self.question = None
        self.answer = None
        self.category = None
        self.bin = 0
        self.reversedBin = 0
        self.tags = None
        self.lastDrillTime = None
        self.updated = False

    def getTagStr(self):
        tagstr = ""
        if not None == self.tags and len(self.tags) > 0:
            if len(self.tags) == 1:
                tagstr = self.tags[0]
            else:
                tagstr = ",".join(self.tags)
        return tagstr
