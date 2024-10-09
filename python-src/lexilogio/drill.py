#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr  8 23:45:44 2023

@author: mathaes
"""

import random
import math
from datetime import datetime
import logging

from lexilogio.deck import Deck
from lexilogio.category import Category
from lexilogio.tag import Tag
import time

class Drill:
    def __init__(self, terms):
        self.terms = terms
        self.cursor = 0

    def advance(self):
        self.cursor += 1

    def isCompleted(self):
        return self.cursor >= len(self.terms)

    def currentTerm(self):
        if self.cursor < 0 or self.cursor > len(self.terms):
            raise Exception(
                f"Drill.currentTerm called with invalid cursor value {self.cursor}"
            )
        return self.terms[self.cursor]

    def assignBinValue(self, binValue, reversedBin=False):
        t = self.currentTerm()
        # NOTE that we always set .update to true now that
        # we are setting timestamp - even if bin value has not changed
        # we want to track when the term was last seen

        t.lastDrillTime = datetime.utcnow().isoformat()
        t.updated = True

        if reversedBin:
            t.reversedBin = binValue
        else:
            t.bin = binValue

    def getUpdatedTerms(self):
        return [t for t in self.terms if t.updated]
    
    def getMissedTerms(self, reversedBin=False):
        if reversedBin:
            return [t for t in self.terms if t.reversedBin <= 2]
        return [t for t in self.terms if t.bin <= 2]

    # Drill construction methods
    def makeDrillFromDeck(deck: Deck, category: Category = None, tag: Tag = None):
        """
        Create a new drill.
        
        If category and tag or both nil, create a drill from all deck terms.
        
        Note that only *one* of category or tag can currently be non-nil
        (drills by tag within a category are TBD).
        
        """
        usingCategory = not None == category
        usingTag = not None == tag
        if usingCategory and usingTag:
            raise Exception("ERROR: a drill can specify a category or a tag, not both")
            
        questionCount = deck.getDrillQuestionCount()
        usingSpacedRep = deck.isUsingSpacedRepetition()
        isReversed = deck.isReversedDrill()

        logging.debug(
            f"Creating drill from deck {deck.name}, category {str(category)}"
        )
        logging.debug(f"reversed: {str(isReversed)}")
        logging.debug(f"using-spaced-repetition: {str(usingSpacedRep)}")

        drill = Drill([])

        if usingSpacedRep:

            binTerms = {}
            for n in range(0, 6):
                if not usingTag:
                    binTerms[n] = deck.getTermsInCategoryOfBinValue(
                        category, n, isReversed
                    )
                else:
                    binTerms[n] = deck.getTermsWithTagOfBinValue(
                        tag, n, isReversed
                    )

            # sanity-check: do we even have enough terms for desired questionCount?
            termTotal = 0
            for n in range(0, 6):
                termTotal += len(binTerms[n])

            logging.debug(f"Available terms: {termTotal}")

            if termTotal == 0:
                print("  no matching terms available; add or input terms to run a drill.")
                return None
            
            # print(f"  termTotal: {termTotal}")
            if questionCount > termTotal:
                questionCount = termTotal
                print(
                    f"  only {termTotal} matching terms available; adjusted questionCount: {questionCount}"
                )

            binDist = deck.getSpacedBinDistribution()


            binCounts = {}
            binSum = 0
            for n in range(0, 6):
                binSum += binDist[n]

            if binSum <= 0:
                logging.error(
                    f"bin distribution values have a 0 or negative sum: {binDist}"
                )
                raise Exception(
                    f"Bad values for bins: {binDist}; fix via preferences"
                )
            for n in range(0, 6):
                binCounts[n] = math.ceil(questionCount * (binDist[n] / binSum))

            desiredDrillTermTotal = 0
            for n in range(0, 6):
                desiredDrillTerms = binCounts[n]
                # print(f"  desired drill terms for bin {n}: {desiredDrillTerms}")
                desiredDrillTermTotal += desiredDrillTerms

            # rounding may have desired term total off by a small amount
            while not desiredDrillTermTotal == questionCount:
                countDiff = desiredDrillTermTotal - questionCount
                if countDiff > 0:
                    # need to reduce binCounts
                    # print("  subtracting one from bin 0 count...")
                    binCounts[0] = binCounts[0] - 1
                    desiredDrillTermTotal -= 1
                else:
                    # need to increase binCounts
                    # print("  adding one to bin 0 count...")
                    binCounts[0] = binCounts[0] + 1
                    desiredDrillTermTotal += 1

            # print("  adjusting bin distributions based on available terms...")

            # first we shift toward the front, then toward the back:
            for n in range(0, 5):
                adjIndex = 5 - n
                shiftToIndex = adjIndex - 1

                shortage = binCounts[adjIndex] - len(binTerms[adjIndex])
                if shortage > 0:
                    # print(
                    #    f"  shifting {shortage} terms from bin {adjIndex} to {shiftToIndex}"
                    # )
                    binCounts[adjIndex] = binCounts[adjIndex] - shortage
                    binCounts[shiftToIndex] = (
                        binCounts[shiftToIndex] + shortage
                    )

            for n in range(0, 5):
                adjIndex = n
                shiftToIndex = adjIndex + 1

                shortage = binCounts[adjIndex] - len(binTerms[adjIndex])
                if shortage > 0:
                    # print(
                    #    f"  shifting {shortage} terms from bin {adjIndex} to {shiftToIndex}"
                    # )
                    binCounts[adjIndex] = binCounts[adjIndex] - shortage
                    binCounts[shiftToIndex] = (
                        binCounts[shiftToIndex] + shortage
                    )

            logging.debug("  FINAL COUNTS FROM EACH BIN:")
            for n in range(0, 6):
                logging.debug(
                    f"  bin[{n}]: {binCounts[n]} from {len(binTerms[n])} available."
                )

            logging.info("  making random term selections...")
            # now we are ready to randomly select terms from each bin
            random.seed(int(time.monotonic()*1000))
            drill.terms = []
            for n in range(0, 6):
                thisBinCount = binCounts[n]
                thisBinTerms = binTerms[n]
                if thisBinCount < len(thisBinTerms):
                    indexSet = set()
                    while len(indexSet) < thisBinCount:
                        indexSet.add(random.randint(0, len(thisBinTerms) - 1))
                    logging.info(f"  index set for bin {n}: {str(indexSet)}")
                    for index in indexSet:
                        drill.terms.append(thisBinTerms[index])
                else:
                    # use all this bin's terms
                    drill.terms.extend(thisBinTerms)

            random.shuffle(drill.terms)

            logging.info(f"  drill completed, {len(drill.terms)} terms chosen.")

        else:  # not using spaced rep from bins, just random from all terms
            sourceTerms = []
            if usingCategory:
                sourceTerms = deck.getTermsInCategory(category)
            elif usingTag:
                sourceTerms = deck.getTermsWithTag(tag)
            else:
                sourceTerms = deck.terms

            if len(sourceTerms) == 0:
                print('No terms !')
                return None

            if questionCount > len(sourceTerms):
                questionCount = len(sourceTerms)

            random.seed()
            drill.terms = []
            if questionCount < len(sourceTerms):
                indexSet = set()
                while len(indexSet) < questionCount:
                    indexSet.add(random.randint(0, len(sourceTerms) - 1))

                for index in indexSet:
                    drill.terms.append(sourceTerms[index])
            else:
                drill.terms.extend(sourceTerms)

            random.shuffle(drill.terms)
            
        return drill
