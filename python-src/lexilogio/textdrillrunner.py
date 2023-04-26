#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Sat Apr  8 23:54:10 2023

@author: mathaes
"""

import sys
import os
import string
import logging

from lexilogio.deckdatabase import DeckDatabase
from lexilogio.term import Term
from lexilogio.drill import Drill
from lexilogio.deck import Deck
from lexilogio.version import LEXILOGIO_PRODUCT_VERSION_STR

from lexilogio.controller import Controller

ARG_DIR = "dir"
ARG_DECK = "deck"
ARG_CATEGORY = "category"
ARG_WEIGHTED = "weighted"
ARG_BINS = "bins"
ARG_COUNT = "count"
ARG_FILE = "file"
ARG_LOGLEVEL = "loglevel"

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

        self.controller: Controller = Controller()

    def initialize(self, dataDir, deckName=None):
        self.controller.initialize(dataDir, deckName)

        # load or create deck
        deck = self.controller.deck
        deckFileName = self.controller.database.getFileName()
        print(
            f"Loaded deck {deck.name} from {deckFileName}, which contains {len(deck.terms)} terms."
        )
        if len(self.controller.deck.terms) == 0:
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
            self.run_prefs()

    def run_mainmenu_input(self):
        print(f"\n{LEXILOGIO_PRODUCT_VERSION_STR}")
        print("---------")
        print(f"current deck: {self.controller.deck.name}")
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
        elif choice == "e":
            self.inputMode = INPUT_MODE_export
            self.run_export()
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
        self.controller.reloadDeck()

        # show a category picker
        drillCategory = self.runCategoryPicker()
        if type(drillCategory) == int and drillCategory == -1:
            # early exit
            self.inputMode = INPUT_MODE_mainmenu
            return

        # build drill from params
        print("\nCreating drill...")
        self.controller.makeNewDrill(category=drillCategory)
        self.drill = self.controller.drill

        if None == self.drill:
            print("ERROR creating drill.")
            self.inputMode = INPUT_MODE_mainmenu
            return

        print("\nStarting drill. Hit return to show answer for each question,")
        print(
            "then rate your knowledge of the answer on a scale of 1-5, where"
        )
        print(
            "1 = not known, 2 = hard to recall, 3 = somewhat known, 4 = familiar, 5 = well known"
        )
        print(" (enter x at any time to exit drill, t to tag a term) ")

        self.inputMode = INPUT_MODE_question

    def runCategoryPicker(self, prompt="Categories:"):
        """
        Prompt for user selection of a category. If wildcard or empty
        selection is made, return None. If 'x' is entered to exit,
        return -1. Otherwise, return the chosen Category object.
        """
        chosenCategory = None

        categoryPickerText = "{prompt}\n  (*) (all categories)\n"
        categories = self.controller.getCategoryList()

        catPickerD = {}
        n = 0
        for catObj in categories:
            alphaKey = string.ascii_lowercase[n]
            catPickerD[alphaKey] = catObj
            categoryPickerText += f"  ({alphaKey}) {catObj.name}\n"
            n = n + 1

        while None == chosenCategory:
            print(categoryPickerText)
            chosenKey = (
                input("Enter letter for category, x to exit: ").strip().lower()
            )
            if chosenKey == "x":
                chosenCategory = -1
                break
            elif chosenKey == "*" or len(chosenKey) == 0:
                chosenCategory = None
                break
            elif not chosenKey in catPickerD:
                print(f"Invalid choice '{chosenKey}'")
                chosenKey = None
            else:
                chosenCategory = catPickerD[chosenKey]

        return chosenCategory

    def run_drill_question_input(self):
        term = self.controller.currentDrillTerm()

        flashQuestion = term.question
        if self.controller.deck.isReversedDrill():
            flashQuestion = term.answer

        ret = input(f"\n\t{flashQuestion}\n").strip().lower()

        if ret == "x":
            self.end_drill()
            return

        self.inputMode = INPUT_MODE_response

    def run_drill_response_input(self):
        # print("DEBUG - run_drill_response_input...")
        term = self.controller.currentDrillTerm()
        flashAnswer = term.answer
        if self.controller.getPref_isReversedDrill():
            flashAnswer = term.question

        rating = 0
        while not rating >= 1 and rating < 5:
            rating = input(f"\t{flashAnswer}\n[1-5]: ").strip().lower()
            if rating == "x":
                self.end_drill()
                return
            if rating == "t":
                print("term tagging not yet implemented - coming soon!...")
                continue
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

        self.controller.setTermBinValue(rating)
        self.controller.advanceDrill()

        self.inputMode = INPUT_MODE_question
        if self.controller.isDrillCompleted():
            self.end_drill()

    def end_drill(self):
        print("Exiting drill...")
        self.controller.saveUpdatedDrillTerms()
        self.inputMode = INPUT_MODE_mainmenu

    def run_export(self):
        category = self.runCategoryPicker("Select category to export:")
        if type(category) == int and category == -1:
            # cancel export
            self.inputMode = INPUT_MODE_mainmenu
            return

        filePath = None
        while None == filePath:
            filePath = input("Enter file path for export (x to exit):")
            if "x" == filePath:
                # cancel export
                self.inputMode = INPUT_MODE_mainmenu
                filePath = None
                break

            if os.path.exists(filePath):
                print(f"An file or folder already exists at path {filePath}.")
                filePath = None
                break

            self.controller.exportTermsToPath(filePath, category)

        self.inputMode = INPUT_MODE_mainmenu

    def run_prefs(self):

        choice = None
        while not choice == "x":
            self.controller.reloadPrefs()

            qcPref = self.controller.getPref_drillQuestionCount()

            spacedRepPref = self.controller.getPref_isUsingSpacedRepetition()

            reversedPref = self.controller.getPref_isReversedDrill()

            binDist = self.controller.getPref_spacedBinDistribution()

            print("\nCurrent lexilogio preferences:")
            print(f" (a) drill question count: {qcPref}")
            print(f" (b) reverse drill (show answers first): {reversedPref}")
            print(f" (c) use spaced repetition: {spacedRepPref}")
            print(f" (d) spaced bin distribution: {binDist}")

            choice = (
                input("\nEnter letter of preference to change, or x to exit: ")
                .strip()
                .lower()
            )
            if choice == "a":
                newCount = int(
                    input("Enter new question count: ").strip().lower()
                )
                if newCount <= 0:
                    print("ERROR: invalid input.")
                else:
                    self.controller.setPref_drillQuestionCount(newCount)

            elif choice == "b":
                toggleReversedPref = not reversedPref
                yn = (
                    input(
                        f"Set 'reverse drill' to {toggleReversedPref}? (y/n): "
                    )
                    .strip()
                    .lower()
                )
                if yn.startswith("y"):
                    self.controller.setPref_isReversedDri(toggleReversedPref)

            elif choice == "c":
                toggleSpaceRep = not spacedRepPref
                yn = (
                    input(
                        f"Set 'use spaced repetition' to {toggleSpaceRep}? (y/n): "
                    )
                    .strip()
                    .lower()
                )
                if yn.startswith("y"):
                    self.controller.getPref_setUsingSpacedRepetition(
                        toggleSpaceRep
                    )
                    self.database.writeDeckPreferences(self.deck)

            elif choice == "d":
                print("bin distribution input not yet implemented...")

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

            # TODO: choose from defined categories?
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

                self.controller.database.insertTerms([newTerm])

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
            self.controller.reloadDeck()

    def do_file_import(self, filePath):
        if not (os.path.isfile(filePath)):
            print(f"ERROR: {filePath} is not a valid file path.")
            return False

        categories = self.controller.getCategoryList()
        runningCategoryPK = None
        catLookup = {}
        for cat in categories:
            catLookup[cat.name] = cat

        importLines = None
        with open(filePath, "r") as importFile:
            importLines = importFile.readlines()

        if None == importLines:
            print("ERROR: failed to read any lines from file.")
            return

        print(
            f"DEBUG - number of lines read from import file: {len(importLines)}"
        )

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
                            newCat = self.controller.addNewCategory(catName)
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
            self.controller.addNewTerms(newTerms)
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
            input(
                "(d) drill (i) import/add (c) categories (t) tags (x) exit: "
            )
            .strip()
            .lower()
        )
        if choice == "d":
            self.prepare_and_run_drill()
        elif choice == "i":
            pass

    def run_tags_edit(self):

        exitTagEditor = False

        while not exitTagEditor:

            currentTags = self.controller.getTagsList()

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
                    print(
                        "ERROR: add command should be followed by new tag name."
                    )
                else:
                    tagName = commandParts[1].strip()
                    if tagName in currentTags:
                        print(f'ERROR: tag "{tagName}" already exists.')
                    else:
                        print(f'Creating tag "{tagName}"...')
                        self.controller.addTag(tagName)

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
                        print(
                            f'WARNING: tag "{tagName}" not found, nothing to delete.'
                        )
                    else:
                        print(f'Deleting tag "{delTagObj.name}"...')
                        self.controller.deleteTag(delTagObj)

        # note, we don't currently change input mode here in case
        # we are editing tags in the midst of a drill

    def run_categories_edit(self):
        exitCatEditor = False

        def catNameSort(catObj):
            return catObj.name

        while not exitCatEditor:

            currentCats = self.controller.getCategoryList()
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
                    print(
                        "ERROR: add command should be followed by new category name."
                    )
                else:
                    catName = commandParts[1].strip()
                    if catName in currentCats:
                        print(f'ERROR: category "{catName}" already exists.')
                    else:
                        print(f'Creating category "{catName}"...')
                        self.controller.addNewCategory(catName)

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
                        self.controller.deleteCategory(delCatObj)

            elif command == "count":
                catsToCount = currentCats
                if len(commandParts) >= 2:
                    catsToCount = []
                    for n in range(1, len(commandParts)):
                        catName = commandParts[n]
                        catObj = self.controller.deck.getCategoryByName(
                            catName
                        )
                        if not None == catObj:
                            catsToCount.append(catObj)

                catsToCount.sort(key=catNameSort)
                print("===============================")
                print("term counts per category")
                for cat in catsToCount:
                    catCount = len(
                        self.controller.deck.getTermsInCategory(cat)
                    )
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

        logLevelStr = "ERROR"

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

            elif arg.startswith(f"{ARG_LOGLEVEL}="):
                logLevelStr = arg[len(ARG_LOGLEVEL) + 1 :].strip().upper()

        # Configure stdout logging
        # TODO also support file logging?
        root = logging.getLogger()
        root.setLevel(logLevelStr)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logLevelStr)
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        root.addHandler(handler)

        # test logging
        logging.debug("Testing debug logging...")
        logging.info("Testing info logging...")
        logging.error("Testing error logging...")

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
                logging.warning("Failed to import anything from {fileArg}")
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


if __name__ == "__main__":
    TextDrillRunner.main(sys.argv)
