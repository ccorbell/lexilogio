#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr  8 23:55:23 2023

@author: mathaes
"""


class Deck:
    PREFSKEY_QUESTION_COUNT = "question.count"
    PREFSKEY_SPACED_REPETITION = "using.spaced.repetition"
    PREFSKEY_REVERSED_DRILL = "reversed.drill"

    def __init__(self, name):
        self.name = name
        self.terms = []
        self.categories = []
        self.tags = []
        self.prefs = {}

    def clear(self):
        """
        Clear all deck data except for name

        Returns
        -------
        None.

        """
        self.terms = []
        self.categories = []
        self.tags = []
        self.prefs = {}

    def getDrillQuestionCount(self):
        return self.prefs[Deck.PREFSKEY_QUESTION_COUNT]

    def isUsingSpacedRepetition(self):
        return self.prefs[Deck.PREFSKEY_SPACED_REPETITION]

    def isReversedDrill(self):
        return self.prefs[Deck.PREFSKEY_REVERSED_DRILL]

    # utilities for filtering terms
    def getTermsInCategory(self, category):
        return [t for t in self.terms if t.category == category]

    def getTermsInCategoryOfBinValue(self, category, binValue, reversedBin):
        if None == category:
            return self.getTermsFromBin(binValue, reversedBin)

        if reversedBin:
            return [
                t
                for t in self.terms
                if t.category == category and t.reversedBin == binValue
            ]
        else:
            return [
                t for t in self.terms if t.category == category and t.bin == binValue
            ]

    def getTermsFromBin(self, binValue, reversedBin):
        if reversedBin:
            return self.getTermsOfReversedBinValue(binValue)
        else:
            return self.getTermsOfBinValue(binValue)

    def getTermsOfBinValue(self, binValue):
        return [t for t in self.terms if t.bin == binValue]

    def getTermsOfReversedBinValue(self, binValue):
        return [t for t in self.terms if t.reversedBin == binValue]

    def getTermsWithTagValue(self, tagValue):
        return [t for t in self.terms if tagValue in t.tags]
