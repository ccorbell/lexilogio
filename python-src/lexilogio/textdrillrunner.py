#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Sat Apr  8 23:54:10 2023

@author: mathaes
"""

import sys
import os
import string

from lexilogio.deckdatabase import DeckDatabase
from lexilogio.term import Term
from lexilogio.drill import Drill
from lexilogio.deck import Deck

ARG_DIR = "dir"
ARG_DECK = "deck"
ARG_CATEGORY = "category"
ARG_WEIGHTED = "weighted"
ARG_BINS = "bins"
ARG_COUNT = "count"
ARG_FILE = "file"

CMD_IMPORT = "import"
CMD_EXPORT = "export"

INPUT_MODE_mainmenu = 0
INPUT_MODE_startDrill = 1
INPUT_MODE_question = 2
INPUT_MODE_response = 3

INPUT_MODE_import = 10
INPUT_MODE_export = 11

INPUT_MODE_add = 20

INPUT_MODE_categories = 30

INPUT_MODE_tags = 40

INPUT_MODE_preferences = 99

INPUT_MODE_batchcmd = 9999


class TextDrillRunner:
    def __init__(self):
        self.inputMode = INPUT_MODE_mainmenu
        self.quit = False
        self.deck = None
        self.drill = None
        self.dataDir = None
        self.dataFilePath = None
        self.database = None

    def initialize(self, dataDir, deckName=None):
        #print("DEBUG - initialize()")
        #print(f" deckName: {deckName}")

        # configure database
        self.dataDir = dataDir
        if not os.path.isdir(self.dataDir):
            print(f"Data directory {self.dataDir} does not exist, creating it...")
            os.makedirs(self.dataDir, exist_ok=True)

        databaseFileName = DeckDatabase.fileNameForDeckName(deckName)
        self.dataFilePath = os.path.join(self.dataDir, databaseFileName)
        self.database = DeckDatabase(self.dataFilePath)

        # load or create deck
        self.deck = self.database.loadDeck(deckName)
        print(
            f"Loaded deck {deckName} from {databaseFileName}, which contains {len(self.deck.terms)} terms."
        )
        if len(self.deck.terms) == 0:
            print(
                "NOTE: loxilogio needs terms to be added before a drill can be run from this deck"
            )
            print("Use the (a) add or (i) import commands from the main menu.")

        # if we have drill parameters, use them to start a new drill

    def run_input(self):
        if self.inputMode == INPUT_MODE_mainmenu:
            self.run_mainmenu_input()
        elif self.inputMode == INPUT_MODE_startDrill:
            self.prepare_and_run_drill()
        elif self.inputMode == INPUT_MODE_question:
            self.run_drill_question_input()
        elif self.inputMode == INPUT_MODE_response:
            self.run_drill_response_input()
        elif self.inputMode == INPUT_MODE_import:
            self.run_import()
        elif self.inputMode == INPUT_MODE_add:
            self.run_add()
        elif self.inputMode == INPUT_MODE_preferences:
            self.τ()

    def run_mainmenu_input(self):
        print("\nlegilogio")
        print("---------")
        print(f"current deck: {self.deck.name}")
        print("commands:")
        print("  (d) drill         (p) preferences    (a) add card")
        print("  (i) import cards  (e) export cards   (m) manage cards")
        print("  (c) categories    (t) tags           (x) exit")

        choice = input(": ").strip().lower()
        if choice == "d":
            self.inputMode = INPUT_MODE_startDrill
            self.prepare_and_run_drill()
        elif choice == "i":
            self.inputMode = INPUT_MODE_import
            self.run_import()
        elif choice == "a":
            self.inputMode = INPUT_MODE_add
            self.run_add()
        elif choice == "p":
            self.inputMode = INPUT_MODE_preferences
            self.run_prefs()  # has its own input loop
            self.inputMode = INPUT_MODE_mainmenu
        elif choice == "c":
            self.inputMode = INPUT_MODE_categories
            self.run_categories_edit()  # has its own input loop
            self.inputMode = INPUT_MODE_mainmenu
        elif choice == "t":
            self.inputMode = INPUT_MODE_tags
            self.run_tags_edit()  # has its own input loop
            self.inputMode = INPUT_MODE_mainmenu
        elif choice == "x":
            sys.exit(0)
        else:
            print(f"Option '{choice}' not recognized.")

    def prepare_and_run_drill(self):
        self.deck = self.database.loadDeck(self.deck.name)

        drillCategory = None
        categoryMenu = "Categories:\n  (*) (all categories)\n"

        drillCatD = {}
        n = 0
        for catObj in self.deck.categories:
            catKey = string.ascii_lowercase[n]
            drillCatD[catKey] = catObj
            categoryMenu += f"  ({catKey}) {catObj.name}\n"
            n = n + 1

        chosenKey = None
        while None == chosenKey:
            print(categoryMenu)
            chosenKey = input("Enter letter for drill category: ").strip().lower()
            if chosenKey == "*" or len(chosenKey) == 0:
                drillCategory = None
                break
            elif not chosenKey in drillCatD:
                print(f"Invalid choice '{chosenKey}'")
                chosenKey = None
            else:
                drillCategory = drillCatD[chosenKey]

        # build drill from params
        print("Creating drill...")
        self.drill = Drill.makeDrillFromDeck(deck=self.deck, category=drillCategory)
        if None == self.drill:
            print("ERROR creating drill.")
            self.inputMode = INPUT_MODE_mainmenu
            return

        print("Starting drill. Hit return to show answer for each question,")
        print("then rate your knowledge of the answer on a scale of 1-5, where")
        print(
            "1 = not known, 2 = hard to recall, 3 = somewhat known, 4 = familiar, 5 = well known"
        )
        print(" (enter x at any time to exit drill) ")

        self.inputMode = INPUT_MODE_question

    def run_drill_question_input(self):
        # print("DEBUG - run_drill_question_input...")
        term = self.drill.currentTerm()
        flashQuestion = term.question
        if self.deck.isReversedDrill():
            flashQuestion = term.answer

        ret = input(f"\n\t{flashQuestion}\n").strip().lower()

        if ret == "x":
            self.end_drill()
            return

        self.inputMode = INPUT_MODE_response

    def run_drill_response_input(self):
        # print("DEBUG - run_drill_response_input...")
        term = self.drill.currentTerm()
        flashAnswer = term.answer
        if self.deck.isReversedDrill():
            flashAnswer = term.question

        rating = 0
        while not rating >= 1 and rating < 5:
            rating = input(f"\t{flashAnswer}\n[1-5]: ").strip().lower()
            if rating == "x":
                self.end_drill()
                return
            try:
                rating = int(rating)
            except ValueError:
                print(
                    f'invalid rating value "{rating}", please enter a value from 1 to 5'
                )
                rating = 0
                continue
            if rating < 1 or rating > 5:
                print(
                    f"invalid rating value {rating}, please enter a value from 1 to 5"
                )
                continue
        self.drill.assignBinValue(rating, self.deck.isReversedDrill())
        self.drill.advance()
        self.inputMode = INPUT_MODE_question
        if self.drill.isComplete():
            self.end_drill()

    def end_drill(self):
        print("Exiting drill...")
        updatedTerms = self.drill.getUpdatedTerms()

        if len(updatedTerms) > 0:
            self.database.updateTermBins(
                self.deck, updatedTerms, self.deck.isReversedDrill()
            )

        self.inputMode = INPUT_MODE_mainmenu

    def run_export(self):
        print("Export not yet implemented...")

    def run_prefs(self):

        choice = None
        while not choice == "x":

            self.database.readDeckPreferences(self.deck)

            qcPref = self.deck.prefs[Deck.PREFSKEY_QUESTION_COUNT]
            spacedRepPref = self.deck.prefs[Deck.PREFSKEY_SPACED_REPETITION]
            reversedPref = self.deck.prefs[Deck.PREFSKEY_REVERSED_DRILL]

            print("\nCurrent lexilogio preferences:")
            print(f" (a) drill question count: {qcPref}")
            print(f" (b) use spaced repetition: {spacedRepPref}")
            print(f" (c) reverse drill (show answers first): {reversedPref}")

            choice = (
                input("\nEnter letter of preference to change, or x to exit: ")
                .strip()
                .lower()
            )
            if choice == "a":
                newCount = int(input("Enter new question count: ").strip().lower())
                if newCount <= 0:
                    print("ERROR: invalid input.")
                else:
                    self.deck.prefs[Deck.PREFSKEY_QUESTION_COUNT] = newCount
                    self.database.writeDeckPreferences(self.deck)

            elif choice == "b":
                toggleSpaceRep = not spacedRepPref
                yn = (
                    input(f"Set 'use spaced repetition' to {toggleSpaceRep}? (y/n): ")
                    .strip()
                    .lower()
                )
                if yn.startswith("y"):
                    self.deck.prefs[Deck.PREFSKEY_SPACED_REPETITION] = toggleSpaceRep
                    self.database.writeDeckPreferences(self.deck)
            elif choice == "c":
                toggleReversedPref = not reversedPref
                yn = (
                    input(f"Set 'reverse drill' to {toggleReversedPref}? (y/n): ")
                    .strip()
                    .lower()
                )
                if yn.startswith("y"):
                    self.deck.prefs[Deck.PREFSKEY_REVERSED_DRILL] = toggleReversedPref
                    self.database.writeDeckPreferences(self.deck)

    def run_add(self):

        done = False
        cancelled = False

        while not (done or cancelled):

            print("Adding card (enter x to cancel):")

            newTerm = Term()

            question = input("question: ")
            if question.strip().lower() == "x":
                cancelled = True
                break
            else:
                newTerm.question = question.strip()

            answer = input("answer: ")
            if answer.strip().lower() == "x":
                cancelled = True
                break
            else:
                newTerm.answer = answer.strip()

            # TODO: choose a defined categories?
            category = input("category: ")
            if category.strip().lower() == "x":
                cancelled = True
                break
            newTerm.category = category.strip()

            # TODO: apply a defined tag?
            tags = input("tags (comma-separated, no spaces): ")
            if tags.strip().lower() == "x":
                cancelled = True
                break
            newTerm.tags = tags.strip().split(",")

            print("Adding card: ")
            print(f" question: {newTerm.question}")
            print(f" answer: {newTerm.answer}")
            print(f" category: {newTerm.category}")
            print(f" tags: {newTerm.tags}")

            confirm = input("confirm? (y/n): ")
            if confirm.strip().lower() == "y":
                done = True

            if done and not newTerm == None:
                print("Saving new card...")
                print(" (not yet implemented) ")

                # TODO: sanity check newTerm - non-empty
                # Q/A, valid category and tags, etc.

                self.database.insertTerms([newTerm])

                # TODO: reload deck?

                yn = input("Add another card? (y/n) ").strip().lower()
                if yn == "n" or yn == "x":
                    self.inputMode = INPUT_MODE_mainmenu
                    break
                else:
                    done = False

        if cancelled:
            print("Import/add cancelled.")
            self.inputMode = INPUT_MODE_mainmenu
            return

    def run_import(self):
        print("\nImport cards from file. (Enter 'x' to cancel during input.)")
        print("Card import files are text with a single line per card.")
        print("The format of each line is")
        print("  question... : answer...\n")
        print("Comment lines beginning with # are ignored, except for ")
        print(
            "# category=NAME which will set the category to NAME for subsequent terms."
        )
        filePath = input("Enter file path: ")
        if filePath.strip().lower() == "x":
            self.inputMode = INPUT_MODE_mainmenu
            return

        importResult = self.do_file_import(filePath)
        if importResult:
            print("Reloading deck...")
            self.deck = self.database.loadDeck(self.deck.name)

    def do_file_import(self, filePath):
        if not (os.path.isfile(filePath)):
            print(f"ERROR: {filePath} is not a valid file path.")
            return False
        
        runningCategoryPK = None
        catLookup = {}
        for cat in self.deck.categories:
            catLookup[cat.name] = cat
        
        importLines = None
        with open(filePath, "r") as importFile:
            importLines = importFile.readlines()

        if None == importLines:
            print("ERROR: failed to read any lines from file.")
            return
        
        print(f"DEBUG - number of lines read from import file: {len(importLines)}")
        
        newTerms = []

        for termLine in importLines:
            # process comments
            if termLine.startswith("#"):
                procLine = termLine.replace("#", "").strip()
                if procLine.startswith("category"):
                    runningCategoryPK = None
                    catTerms = procLine.split("=")
                    if len(catTerms) == 2:
                        newCat = None
                        catName = catTerms[1].strip()
                        if catName in catLookup:
                            newCat = catLookup[catName]
                        else:
                            print(f"CREATING NEW CATEGORY: {catName}")
                            newCat = self.database.insertDeckCategory(self.deck, catName)
                            self.deck.categories.append(newCat)
                            catLookup[catName] = newCat
                            
                        runningCategoryPK = newCat.pkey
                        print(f"Importing terms with category {catName}")                        
                    else:
                        raise Exception(
                            f"ERROR - category line should have the format # category=(value), found:\n{termLine}"
                        )
                continue

            # if line is all-whitespace, skip it
            if len(termLine.strip()) == 0:
                continue

            termQA = termLine.strip().split(":")
            if len(termQA) == 2:
                newTerm = Term()
                newTerm.question = termQA[0].strip()
                newTerm.answer = termQA[1].strip()
                if not None == runningCategoryPK:
                    newTerm.category = runningCategoryPK
                newTerms.append(newTerm)

        if len(newTerms) > 0:
            print(f"Importing {len(newTerms)} terms...")
            self.database.insertTerms(self.deck, newTerms)
            return True
        else:
            print("No terms found to import in file {filePath}")
            return False


    def do_file_export(self, filePath):
        print("File export not yet implemented")
        return False

    def show_setup_menu(self):
        print("legilogio")
        print("---------")
        print("current deck: {self.deck.name}")

        choice = (
            input("(d) drill (i) import/add (c) categories (t) tags (x) exit: ")
            .strip()
            .lower()
        )
        if choice == "d":
            self.prepare_and_run_drill()
        elif choice == "i":
            pass

    def run_tags_edit(self):

        exitTagEditor = False
        
        def tagNameSort(tag):
            return tag.name
            
        while not exitTagEditor:
            
            
            currentTags = self.database.getDeckTags(self.deck)
            currentTags.sort(key=tagNameSort)

            print(
                "\nEdit tags list. Tags must have no spaces and are case-insensitive.\nCurrent tags:"
            )
            if len(currentTags) == 0:
                print("  None")
            else:
                for curTag in currentTags:
                    print(f"  {curTag.name}")

            print("\ncommands: add (tag-name), delete (tag-name), x (exit)")
            commandInput = input(": ")

            commandParts = commandInput.lower().split(" ")
            command = commandParts[0].strip()
            if command == "x":
                exitTagEditor = True
                break
            elif command == "add":
                if len(commandParts) < 2:
                    print("ERROR: add command should be followed by new tag name.")
                else:
                    tagName = commandParts[1].strip()
                    if tagName in currentTags:
                        print(f'ERROR: tag "{tagName}" already exists.')
                    else:
                        print(f'Creating tag "{tagName}"...')
                        newTag = self.database.insertDeckTag(self.deck, tagName)
                        self.deck.tags.append(newTag)
            elif command == "delete":
                if len(commandParts) < 2:
                    print(
                        "ERROR: delete command should be followed name of tag to delete."
                    )
                else:
                    tagName = commandParts[1].strip()
                    delTagObj = None
                    for tagObj in currentTags:
                        if tagObj.name.lower() == tagName.lower():
                            delTagObj = tagObj

                    if None == delTagObj:
                        print(f'WARNING: tag "{tagName}" not found, nothing to delete.')
                    else:
                        print(f'Deleting tag "{delTagObj.name}"...')
                        self.database.deleteDeckTag(self.deck, delTagObj)

        # note, we don't currently change input mode here in case
        # we are editing tags in the midst of a drill

    def run_categories_edit(self):
        exitCatEditor = False

        def catNameSort(catObj):
            return catObj.name        

        while not exitCatEditor:

            currentCats = self.database.getDeckCategories(self.deck)
            currentCats.sort(key=catNameSort)

            print("\nEdit categories list.\nCurrent categories:")
            if len(currentCats) == 0:
                print("  None")
            else:
                for curCat in currentCats:
                    print(f"  {curCat.name}")

            print(
                "\ncommands:\n  add (category-name), delete (category-name), count (category-name), x (exit)"
            )
            commandInput = input(": ")

            commandParts = commandInput.lower().split(" ")
            command = commandParts[0].strip()
            if command == "x":
                exitCatEditor = True
                break
            elif command == "add":
                if len(commandParts) < 2:
                    print("ERROR: add command should be followed by new category name.")
                else:
                    catName = commandParts[1].strip()
                    if catName in currentCats:
                        print(f'ERROR: category "{catName}" already exists.')
                    else:
                        print(f'Creating category "{catName}"...')
                        newCat = self.database.insertDeckCategory(self.deck, catName)
                        self.deck.categories.append(newCat)
                        
            elif command == "delete":
                if len(commandParts) < 2:
                    print(
                        "ERROR: delete command should be followed name of category to delete."
                    )
                else:
                    catName = commandParts[1].strip()
                    delCatObj = None
                    for catObj in currentCats:
                        if catObj.name == catName:
                            delCatObj = catObj
                            break
                        
                    if None == delCatObj:
                        print(
                            f'WARNING: category "{catName}" not found, nothing to delete.'
                        )
                    else:
                        print(f'Deleting category "{catName}"...')
                        self.database.deleteDeckCategory(self.deck, delCatObj)
                        self.deck.categories.remove(delCatObj)
                        
            elif command == "count":
                catsToCount = currentCats
                if len(commandParts) >= 2:
                    catsToCount = []
                    for n in range(1, len(commandParts)):
                        catName = commandParts[n]
                        catObj = self.deck.getCategoryByName(catName)
                        if not None == catObj:
                            catsToCount.append(catObj)
                            
                catsToCount.sort(key=catNameSort)
                print("===============================")
                print("term counts per category")
                for cat in catsToCount:
                    catCount = len(self.deck.getTermsInCategory(cat))
                    print(f"  {cat.name}: {catCount}")
                print("===============================")

        # note, we don't currently change input mode here in case
        # we are editing tags in the midst of a drill

    def main(argv):
        dataDir = os.path.join(os.environ["HOME"], ".lexilogio")

        deckName = "el_en"  # default

        fileArg = None

        foundImportCmd = False
        foundExportCmd = False

        for arg in argv:

            if arg.strip() == CMD_IMPORT:
                foundImportCmd = True

            elif arg.strip() == CMD_EXPORT:
                foundExportCmd = True

            elif arg.startswith(f"{ARG_DIR}="):
                dataDir = arg[len(ARG_DIR) + 1 :]

            elif arg.startswith(f"{ARG_DECK}="):
                deckName = arg[len(ARG_DECK) + 1 :]

            elif arg.startswith(f"{ARG_FILE}="):
                fileArg = arg[len(ARG_FILE) + 1 :]

        runner = TextDrillRunner()
        runner.initialize(dataDir, deckName)

        if foundImportCmd:
            if None == fileArg:
                print("ERROR: import command requires file=PATH parameter")
                sys.exit(1)
            runner.inputMode = INPUT_MODE_batchcmd
            if runner.do_file_import(fileArg):
                return
            else:
                print("Failed to import anything from {fileArg}")
                sys.exit(1)

        if foundExportCmd:
            if None == fileArg:
                print("ERROR: export command requires file=PATH parameter")
                sys.exit(1)
            runner.inputMode = INPUT_MODE_batchcmd
            if runner.do_file_export(fileArg):
                return
            else:
                sys.exit(1)

        runner.inputMode = INPUT_MODE_mainmenu
        while not runner.quit:
            runner.run_input()


def importAllGreekFiles():
    adjFile = (
        "/Users/mathaes/Documents/Research/Έλληνικα/flashy/greek-adjectives-master.txt"
    )
    advFile = (
        "/Users/mathaes/Documents/Research/Έλληνικα/flashy/greek-adverbs-master.txt"
    )
    conjFile = "/Users/mathaes/Documents/Research/Έλληνικα/flashy/greek-conjunctions-master.txt"
    nounFile = (
        "/Users/mathaes/Documents/Research/Έλληνικα/flashy/greek-nouns-master.txt"
    )
    prepFile = "/Users/mathaes/Documents/Research/Έλληνικα/flashy/greek-prepositions-master.txt"
    phraseFile = (
        "/Users/mathaes/Documents/Research/Έλληνικα/flashy/greek-phrases-master.txt"
    )
    pronounFile = (
        "/Users/mathaes/Documents/Research/Έλληνικα/flashy/greek-pronouns-master.txt"
    )
    verbsFile = (
        "/Users/mathaes/Documents/Research/Έλληνικα/flashy/greek-verbs-master.txt"
    )

    importFiles = [
        adjFile,
        advFile,
        conjFile,
        nounFile,
        prepFile,
        phraseFile,
        pronounFile,
        verbsFile,
    ]
    for impFile in importFiles:
        TextDrillRunner.main(["deck=el_en", "import", f"file={impFile}"])


if __name__ == "__main__":
    print("DEBUG running TextDrillRunner.main()...")
    TextDrillRunner.main(["deck=el_en"])
    # TextDrillRunner.main(sys.argv)
