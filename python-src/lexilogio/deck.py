#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr  8 23:55:23 2023

@author: mathaes
"""

from lexilogio.category import Category
from lexilogio.tag import Tag
import random

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

    def removeTerm(self, term):
        if term in self.terms:
            self.terms.remove(term)
        
    # utilities for filtering terms

    def getAllTerms(self):
        return self.terms
    
    def getRandomTerms(self, count):
        if count <= 0:
            return []
        if count >= len(self.terms):
            return self.terms
        
        result = []
        term_index_set = set()
        while len(term_index_set) < count:
            term_index_set.add(random.randint(0, len(self.terms)))
        
        for index in term_index_set:
            result.append(self.terms[index])
    
        return result

    def getTermsInCategory(self, category: Category):
        return [t for t in self.terms if t.category == category.pkey]
    
    def getTermByPKey(self, pkey):
        #print(f"DEBUG - checking {len(self.terms)} terms for pkey {pkey}...")
        for t in self.terms:
            #print(f"  {str(t)}")
            if t.pkey == pkey:
                return t
        return None

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
        
    def getTermsWithTag(self, tag: Tag):
        if tag.pkey in self.tagToTerms:
            termPKs = self.tagToTerms[tag.pkey]
            return [t for t in self.terms if t.pkey in termPKs]
        return []
    
    def getTermsWithTagOfBinValue(self, tag: Tag, binValue, reversedBin):
        if None == tag:
            return self.getTermsFromBin(binValue, reversedBin)
        
        tagTerms = self.getTermsWithTag(tag)
        if len(tagTerms) == 0:
            return tagTerms
    
        if reversedBin:
            return [t for t in tagTerms if t.reversedBin == binValue]
        else:
            return [t for t in tagTerms if t.bin == binValue]

    def getTermsFromBin(self, binValue, reversedBin):
        if reversedBin:
            return self.getTermsOfReversedBinValue(binValue)
        else:
            return self.getTermsOfBinValue(binValue)

    def getTermsOfBinValue(self, binValue):
        return [t for t in self.terms if t.bin == binValue]

    def getTermsOfReversedBinValue(self, binValue):
        return [t for t in self.terms if t.reversedBin == binValue]
    
    def getTagsForTerm(self, term):
        tags = []
        if term.pkey in self.termToTags:
            tagPKs = self.termToTags[term.pkey]
            tags = [tg for tg in self.tags if tg.pkey in tagPKs]
        return tags

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
