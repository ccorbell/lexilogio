#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Apr 23 16:14:53 2023

@author: mathaes
"""

import logging
import os

from lexilogio.category import Category
from lexilogio.deckdatabase import DeckDatabase
from lexilogio.deck import Deck
from lexilogio.drill import Drill
from lexilogio.tag import Tag
from lexilogio.term import Term


class ControllerClient:
    def __init__(self):

        pass

    def handleError(
        self, actionIdentifier, errorIdentifier, userMessage, detail
    ):
        logging.error(
            f"{userMessage} ({actionIdentifier}:{errorIdentifier}) {detail}"
        )

    def handleSuccess(self, actionIdentifier):
        logging.debug(f"({actionIdentifier}) SUCCESS")

    def handleNotification(self, notificationIdentifier, notificationData):
        pass


class Controller:
    """
    The Controller class is a UI-independent controller for the
    lexilogio back-end state and data. A single controller instance manages
    a single Deck and runs a single Drill at a time.

    The goal of this class is to coordinate the model and data implementation
    into application business logic that any type of front-end can adopt
    (text/terminal, desktop GUI, web UI, etc.)

    Apart from its direct API, the Controller class supports
    a notification scheme that permits a UI client to handle events in
    a versatile and potentially asynchronous way.
    """

    def __init__(self):
        self.deckName = None
        self.deck: Deck = None
        self.drill: Drill = None
        self.database: DeckDatabase = None

        self.dataDir = None
        self.dataFilePath = None

    def initialize(self, dataDir, deckName):
        self.deckName = deckName
        self.dataDir = dataDir
        if not os.path.isdir(self.dataDir):
            logging.info(
                f"Data dir {self.dataDir} does not exist, creating it..."
            )
            os.makedirs(self.dataDir, exist_ok=True)

        databaseFileName = DeckDatabase.fileNameForDeckName(deckName)
        self.dataFilePath = os.path.join(self.dataDir, databaseFileName)
        self.database = DeckDatabase(self.dataFilePath)

        # load or create deck
        self.reloadDeck()

    def reloadDeck(self):
        self.deck = self.database.loadDeck(self.deckName)

    def getCategoryList(self):
        return self.deck.categories
    
    def getCategoryByName(self, categoryName):
        return self.deck.getCategoryByName(categoryName)

    def addNewCategory(self, categoryName):
        newCat = self.database.insertDeckCategory(self.deck, categoryName)
        self.deck.categories.append(newCat)
        return newCat

    def deleteCategory(self, category: Category):
        self.database.deleteDeckCategory(self.deck, category)
        self.deck.categories.remove(category)

    def getTagsList(self):
        def tagNameSort(tag):
            return tag.name

        tags = self.database.getDeckTags(self.deck)
        tags.sort(key=tagNameSort)
        return tags

    def addTag(self, tagName):
        newTag = self.database.insertDeckTag(self.deck, tagName)
        self.deck.tags.append(newTag)
        return newTag
    
    def applyTagToTerm(self, tag:Tag, term:Term):
        self.database.applyTagToTerm(self.deck, term, tag)

    def deleteTag(self, tag: Tag):
        self.database.deleteDeckTag(self.deck, tag)

    def addNewTerms(self, newTermList):
        self.database.insertTerms(self.deck, newTermList)

    # -------------------------------------- Deck Preferences
    def reloadPrefs(self):
        self.database.readDeckPreferences(self.deck)

    def getPref_drillQuestionCount(self):
        return self.deck.getDrillQuestionCount()

    def setPref_drillQuestionCount(self, newCount: int):
        self.deck.prefs[Deck.PREFSKEY_QUESTION_COUNT] = newCount
        self.database.writeDeckPreferences(self.deck)

    def getPref_isReversedDrill(self):
        return self.deck.isReversedDrill()

    def setPref_isReversedDri(self, is_reversed: bool):
        self.deck.prefs[Deck.PREFSKEY_REVERSED_DRILL] = is_reversed
        self.database.writeDeckPreferences(self.deck)

    def getPref_isUsingSpacedRepetition(self):
        return self.deck.isUsingSpacedRepetition()

    def getPref_setUsingSpacedRepetition(self, use_spaced_rep: bool):
        self.deck.prefs[Deck.PREFSKEY_SPACED_REPETITION] = use_spaced_rep
        self.database.writeDeckPreferences(self.deck)

    def getPref_spacedBinDistribution(self):
        return self.deck.getSpacedBinDistribution()

    def setPref_spacedBinDistribution(self, binDist):
        self.deck.prefs[Deck.PREFSKEY_SPACED_BIN_DISTRIBUTION] = binDist
        self.database.writeDeckPreferences(self.deck)

    # -------------------------------------- Drill

    def makeNewDrill(self, category: Category = None, tag: Tag = None):
        self.drill = Drill.makeDrillFromDeck(deck=self.deck, category=category, tag=tag)
        # TODO notify that drill was created successfull

    def currentDrillTerm(self):
        return self.drill.currentTerm()

    def setTermBinValue(self, binValue):
        self.drill.assignBinValue(binValue, self.deck.isReversedDrill())

    def advanceDrill(self):
        self.drill.advance()

    def isDrillCompleted(self):
        return self.drill.isCompleted()

    def saveUpdatedDrillTerms(self):
        updatedTerms = self.drill.getUpdatedTerms()
        logging.debug(f"Saving {len(updatedTerms)} updated terms...")
        if len(updatedTerms) > 0:
            self.database.updateTermBins(
                self.deck, updatedTerms, self.deck.isReversedDrill()
            )

    # -------------------------------------- Import and Export
    def exportTermsToPath(self, filePath, category: Category = None):
        self.reloadDeck()
        termList = None

        categoryList = []
        if None == category:
            categoryList = self.deck.categories
        else:
            categoryList = [category]

        logging.debug(
            f"Exporting terms for categories {categoryList} to file {filePath}..."
        )
        exportText = ""
        for exportCat in categoryList:
            exportText += f"# category={exportCat.name}\n"
            termList = self.deck.getTermsInCategory(exportCat)
            termList.sort(key=Term.questionSort)

            for term in termList:
                exportText += f"{term.question}: {term.answer}\n"

        # TODO: also export terms with no category?
        with open(filePath, "w") as exportFileObj:
            exportFileObj.write(exportText)

        if os.path.isfile(filePath):
            print("Export complete.")
        else:
            print("UNEXPECTED ERROR: filed to write file.")
