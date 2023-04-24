#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr  8 23:55:23 2023

@author: mathaes
"""

from lexilogio.category import Category


class Deck:
    PREFSKEY_QUESTION_COUNT = "question.count"
    PREFSKEY_SPACED_REPETITION = "using.spaced.repetition"
    PREFSKEY_REVERSED_DRILL = "reversed.drill"
    PREFSKEY_SPACED_BIN_DISTRIBUTION = "spaced.bin.distribution"

    def __init__(self, name):
        self.name = name
        self.terms = []
        self.categories = []
        self.tags = []
        self.termToTags = {}  # term pkey -> array of tag pkey
        self.tagToTerms = {}  # tag pkey -> array of term pkey
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

    def isReversedDrill(self):
        return self.prefs[Deck.PREFSKEY_REVERSED_DRILL]

    def isUsingSpacedRepetition(self):
        return self.prefs[Deck.PREFSKEY_SPACED_REPETITION]

    def getSpacedBinDistribution(self):
        return self.prefs[Deck.PREFSKEY_SPACED_BIN_DISTRIBUTION]

    # utilities for filtering terms
    def getTermsInCategory(self, category: Category):
        return [t for t in self.terms if t.category == category.pkey]

    def getTermsInCategoryOfBinValue(
        self, category: Category, binValue, reversedBin
    ):
        if None == category:
            return self.getTermsFromBin(binValue, reversedBin)

        if reversedBin:
            return [
                t
                for t in self.terms
                if t.category == category.pkey and t.reversedBin == binValue
            ]
        else:
            return [
                t
                for t in self.terms
                if t.category == category.pkey and t.bin == binValue
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

    def getCategoryByName(self, catName):
        for cat in self.categories:
            if cat.name == catName:
                return cat
        return None

    def getCategoryByPK(self, catPK):
        for cat in self.categories:
            if cat.pkey == catPK:
                return cat
        return None
