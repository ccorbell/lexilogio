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
        self.lastDrillTime = None
        self.updated = False
        self.hasPaperCard = False
        self.tags = None

    def questionSort(term):
        return term.question
    
    def __repr__(self):
        return f"[{self.pkey}] {self.question}: {self.answer}"
