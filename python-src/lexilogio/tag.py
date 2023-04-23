#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr 22 11:25:32 2023

@author: mathaes
"""


class Tag:
    def __init__(self, name="", pkey=None):
        self.name = name
        self.pkey = pkey


class TagTermRelation:
    def __init__(self, tag_pkey, term_pkey):
        self.tag_pkey = tag_pkey
        self.term_pkey = term_pkey
