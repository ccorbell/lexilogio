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
import copy

from lexilogio.deckdatabase import QueryCriterion
from lexilogio.term import Term
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

INPUT_MODE_manageTerms = 50

INPUT_MODE_randomWords = 60

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

    def print_stats(self):
        stats = self.controller.get_stats()
        score = stats["score"]
        rev_score = stats["reverse-score"]
        term_count = stats["count"]
        avg = "{:.4f}".format(stats["average"])
        rev_avg = "{:.4f}".format(stats["reverse-average"])
        
        print(f"  SCORE: {score}  REVERSE SCORE: {rev_score}")
        print(f"  ({term_count} terms, {avg} average, {rev_avg} reverse-average)")
        
    def run_mainmenu_input(self):
        print(f"\n{LEXILOGIO_PRODUCT_VERSION_STR}")
        print("---------")
        print(f"current deck: {self.controller.deck.name}")
        self.print_stats()
        print("commands:")
        print("  (d) drill         (p) preferences    (a) add card")
        print("  (i) import cards  (e) export cards   (m) manage cards")
        print("  (c) categories    (t) tags           (r) random-words")
        print("  (L) reload database            (x) exit")

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
        elif choice == "m":
            self.inputMode = INPUT_MODE_manageTerms
            self.run_manage_terms()
            self.inputMode = INPUT_MODE_mainmenu
        elif choice == "r":
            self.inputMode = INPUT_MODE_randomWords
            self.run_random_words()
            self.inputMode = INPUT_MODE_mainmenu
        elif choice == "l":
            self.controller.reloadDeck()
            print("Deck reloaded.")
        elif choice == "x":
            sys.exit(0)
        else:
            print(f"Option '{choice}' not recognized.")

    def prepare_and_run_drill(self):
        self.controller.reloadDeck()

        drillTag = None
        drillCategory = None
        earlyExit = False
        
        typeChoice = input("Enter drill type: (c) category, (t) tag, (a or return) all terms: ").strip().lower()
        
        if typeChoice == 'c':
            # show a category picker
            drillCategory = self.runCategoryPicker()
            if type(drillCategory) == int and drillCategory == -1:
                earlyExit = True
        elif typeChoice == 't':
            # show a tag picker
            drillTag = self.runTagPicker(permit_new_tag=False)
            if type(drillTag) == int and drillTag == -1:
                earlyExit = True
        elif typeChoice == 'x':
            earlyExit = True
            
        if earlyExit:
            self.inputMode = INPUT_MODE_mainmenu
            return
        
        # build drill from params
        print("\nCreating drill...")
        self.controller.makeNewDrill(category=drillCategory, tag=drillTag)
        self.drill = self.controller.drill

        if None == self.drill:
            print("ERROR creating drill.")
            self.inputMode = INPUT_MODE_mainmenu
            return

        print(f"\nStarting drill with {len(self.drill.terms)} terms.")
        print("Hit return to show answer for each question,")
        print(
            "then rate your knowledge of the answer on a scale of 1-5, where"
        )
        print(
            "1 = not known, 2 = hard to recall, 3 = somewhat known, 4 = familiar, 5 = well known"
        )
        print(" (enter x at any time to exit drill, t to tag a term) ")

        self.inputMode = INPUT_MODE_question

    def runCategoryPicker(self, prompt="Categories:", allow_wildcard=False):
        """
        Prompt for user selection of a category. If wildcard or empty
        selection is made, return None. If 'x' is entered to exit,
        return -1. Otherwise, return the chosen Category object.
        """
        chosenCategory = None

        categoryPickerText = f"{prompt}\n"
        
        if allow_wildcard:
            categoryPickerText += "  (*) (all categories)\n"
            
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
                if allow_wildcard:
                    break
            elif not chosenKey in catPickerD:
                print(f"Invalid choice '{chosenKey}'")
                chosenKey = None
            else:
                chosenCategory = catPickerD[chosenKey]

        return chosenCategory

    def runTagPicker(self, prompt="Tags:", permit_new_tag=True, allow_none=False):
        """
        Prompt for user selection of a tag. If wildcard or empty
        selection is made, return None. If 'x' is entered to exit,
        return -1. Otherwise, return the chosen Tag object.
        """
        chosenTag = None

        tagPickerText = f"{prompt}\n"
        tags = self.controller.getTagsList()
        tag_names = [tag.name for tag in tags]
        
        tagPickerD = {}
        n = 0
        for tagObj in tags:
            alphaKey = string.ascii_lowercase[n]
            tagPickerD[alphaKey] = tagObj
            tagPickerText += f"  ({alphaKey}) {tagObj.name}\n"
            n = n + 1
            
        if permit_new_tag:
            tagPickerText += "  (+) new tag\n"
        
        while None == chosenTag:
            print(tagPickerText)
            chosenKey = (
                input("Enter letter for tag, x to exit: ").strip().lower()
            )
            if len(chosenKey) == 0:
                if allow_none:
                    return None
                else:
                    print("Empty entry not allowed; enter x to cancel.")
                    continue
            if chosenKey == "x":
                chosenTag = -1
                break
            elif chosenKey == "+":
                new_tag_name = input("Enter new tag name: ").strip().lower()
                if len(new_tag_name) == 0:
                    continue
                
                if new_tag_name in tag_names:
                    print(f"Tag {new_tag_name} already exists.")
                    continue
                
                new_tag = self.controller.addTag(new_tag_name)
                return new_tag
                
            elif not chosenKey in tagPickerD:
                print(f"Invalid choice '{chosenKey}'")
                chosenKey = None
            else:
                chosenTag = tagPickerD[chosenKey]

        return chosenTag

    

    def run_apply_tag_to_term(self):
        term = self.controller.currentDrillTerm()
        doneTagging = False

        while not doneTagging:
            # choose tag
            tagPickerList = ""
            tagD = {}
            tags = self.controller.getTagsList()
            n = 0
            for tag in tags:
                alphaKey = string.ascii_lowercase[n]
                tagD[alphaKey] = tag
                tagPickerList += f"  ({alphaKey}) {tag.name}\n"
                n = n + 1
            print(tagPickerList)

            chosenTag = None
            while None == chosenTag:
                chosenKey = input(
                    "Enter tag, + to add a new tag, x to exit: "
                ).strip()
                print(f"chosenKey: {chosenKey}")
                
                if chosenKey in tagD:
                    chosenTag = tagD[chosenKey]
                    print(f" - applying tag {chosenTag.name} to term.")
                    self.controller.applyTagToTerm(chosenTag, term)
                elif chosenKey == "+":
                    newTag = None
                    while newTag == None:
                        newTagName = input("New tag name: ").strip()
                        if len(newTagName) == 0:
                            continue
                        elif newTagName in tagD:
                            print(f'  tag "{newTagName}" already exists.')
                        else:
                            chosenTag = self.controller.addTag(newTagName)
                            print(
                                f" - added tag {newTagName}, applying to term."
                            )
                            self.controller.applyTagToTerm(chosenTag, term)
                elif chosenKey == "x":
                    return
                else:
                    print("Unrecognized choice '{chosenKey}'")

                if chosenTag:
                    yn = input("Apply another tag? (y/n) ").strip().lower()
                    doneTagging = yn.startswith("n")
                    if not doneTagging:
                        chosenTag = None
            

    def run_drill_question_input(self):
        term = self.controller.currentDrillTerm()

        flashQuestion = term.question
        if self.controller.deck.isReversedDrill():
            flashQuestion = term.answer

        ret = input(f"\n\t{flashQuestion}\n").strip().lower()

        if ret == "x":
            self.end_drill()
            return
        elif ret == "t":
            self.run_apply_tag_to_term()

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
                self.run_apply_tag_to_term()
                rating = 0
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
        missed_terms = self.controller.getMissedDrillTerms()
        numMissed = len(missed_terms)
        if numMissed > 0:
            # prompt to tag missed terms
            suffix = "s"
            if numMissed == 1:
                suffix = ""
            prompt = f"{numMissed} term{suffix} scored 2 or less; would you like to tag them? (y/n) "
            yn = input(prompt).strip().lower()
            if yn.startswith('y'):
                self.tag_missed_terms(missed_terms)
                
        self.controller.saveUpdatedDrillTerms()
        self.inputMode = INPUT_MODE_mainmenu

    def tag_missed_terms(self, missed_terms):
        tag = self.runTagPicker(permit_new_tag=True)
        if tag is not None and tag != -1:
            for term in missed_terms:
                self.controller.applyTagToTerm(tag, term)
        
    def run_manage_terms(self):
        print("============")
        print("Manage terms")
        print("============")
        print("This mode lets you query for terms by a variety of criteria")
        print("and modify or delete terms by referencing their id values.")
        
        exit_manage_terms = False
        
        while not exit_manage_terms:
            print(" menu:")
            print("   q - query for terms")
            print("   e - edit term")
            print("   x - exit term manager")
            choice = input(" > ").strip().lower()
            
            if choice == 'q':
                self.query_for_manage_terms()
            elif choice == 'e':
                self.manage_terms_editor()
            elif choice == 'x':
                exit_manage_terms = True
                print("DEBUG - exiting term manager...")
                return
        
    def run_random_words(self):
        print("===================")
        print("select random words")
        print("===================")
        
        exit_random_words = False
        
        while not exit_random_words:
            user_input = input("enter number of words (x to exit): ").strip().lower()
            if user_input == 'x':
                exit_random_words = True
                return
            if user_input.isnumeric():
                num_terms = int(user_input)
                if num_terms > 0:
                    terms = self.controller.getRandomTerms(num_terms)
                    for term in terms:
                        print(str(term))
            
                
                
        
    def query_for_manage_terms(self):
        query = []
        building_query = True
        while building_query:
            print(f" Current query: {query}")
            print("   c - add category")
            print("   t - add tag")
            print("   q - add question")
            print("   a - add answer")
            print("   b - add bin value")
            print("   r - add reverse bin value")
            print("   0 - reset query")
            print("   x - exit (cancel query)")
            print(" Or hit return to run query")
            choice = input("> ").strip().lower()
            
            if choice == "":
                break
            
            if choice == 'c':
                cat = self.runCategoryPicker("Choose category:")
                if None == cat:
                    continue
                elif type(cat) == int and cat == -1:
                    continue
                else:
                    query.append( QueryCriterion.category(cat) )
                    
            elif choice == 't':
                tag = self.runTagPicker("Choose tag:")
                if None == tag:
                    print("...no tag selected, ignoring.")
                    continue
                elif type(tag) == int and cat == -1:
                    print("...no tag selected, ignoring.")
                    continue
                else:
                    query.append( QueryCriterion.tag(tag) )
                
            elif choice == "q":
                questionText = input("Enter question text; use * for wildcard, x to cancel: ").strip()
                if len(questionText) > 0:
                    if questionText == 'x':
                        continue
                    
                    query.append( QueryCriterion.question(questionText) )
            
            elif choice == "a":
                answerText = input("Enter answer text; use * for wildcard, x to cancel: ").strip()
                if len(answerText) > 0:
                    if answerText == 'x':
                        continue
                    
                    query.append( QueryCriterion.answer(answerText) )
                    
            elif choice == "b":
                binText = input("Enter bin value (0-5), x to cancel: ").strip()
                if len(binText) > 0:
                    if binText == 'x':
                        continue
                    
                    query.append( QueryCriterion.binvalue(binText) )
                    
            elif choice == "r":
                rbinText = input("Enter reverse-bin value (0-5), x to cancel: ").strip()
                if len(rbinText) > 0:
                    if rbinText == 'x':
                        continue
                    
                    query.append( QueryCriterion.reversebinvalue(rbinText) )
                    
            elif choice == '0':
                query = []
                print("Query reset.")
                continue
            
            elif choice == 'x':
                building_query = False
                print("Query canceled.")
                return
                
        results = self.controller.query(query)
        print("Query results:")
        if None == results or len(results) == 0:
            print("None")
        else:
            print("[ID] question: answer")
            print("---- --------  ------")
            for result in results:
                print(f"[{result.pkey}] {result.question}: {result.answer}")
    
    def manage_terms_editor(self):
        
        exit_term_editor = False
        while not exit_term_editor:
            # first the user must choose a term to edit
            
            termID = 0
            term = None
            
            while term == None:
                termIdStr = input("Enter ID of card to edit: ").strip()
                if len(termIdStr) > 0:
                    if termIdStr == 'x':
                        return
                    
                    try:
                        termID = int(termIdStr)
                    except ValueError:
                        print(f"ERROR: expected integer, got \"{termIdStr}\"")
                        
                    if termID > 0:
                        print(f"DEBUG: termID is {termID}")
                        term = self.controller.getTerm(termID)
                        if None == term:
                            print(f"No card found with ID {termIdStr}.")
                     
            # Now that a card has been selected show edit menu
            while not term == None:
                print("Editing card:")
                print(f"[{term.pkey}] {term.question}: {term.answer}")
                # get category
                cat = self.controller.getCategoryByPkey(term.category)
                print(f"Category: {str(cat)}")
                tags = self.controller.getTagsForTerm(term)
                if None == tags or len(tags) == 0:
                    print("Tags: None")
                else:
                    tagNames = list(map(lambda tag: tag.name, tags))
                    tagCommaStr = ", ".join(tagNames)
                    print(f"Tags: {tagCommaStr}")
            
                print ("  (q) edit question")
                print ("  (a) edit answer")
                print ("  (c) change category")
                print ("  (t) add tag")
                print ("  (-) remove tag")
                print ("  (d) delete term")
                print ("  (x) exit")
                choice = input("> ").strip().lower()
                
                if choice == 'x':
                    term = None
                    exit_term_editor = True
                    break
                elif choice == 'c':
                    self.assign_category_for_manage_terms(term)
                elif choice == 't':
                    self.tag_for_manage_terms(term)
                elif choice == '-':
                    self.tag_for_manage_terms(term, removing=True)
                elif choice == 'd':
                    self.delete_for_manage_terms(term)
                    term = None
                    break
                elif choice == 'q' or choice == 'a':
                    modifying = 'question'
                    if choice == 'a':
                        modifying = 'answer'
                    new_value = input(f"Enter new {modifying}\n> ")
                    if len(new_value.strip()) == 0:
                        print("Invalid value.")
                        continue
                    yn = input(f"Confirm: set {modifying} to {new_value}?\n(y/n) ").strip().lower()
                    if not yn.startswith("y"):
                        print("No change applied.")
                        continue
                    if choice == 'q':
                        term.question = new_value
                    else:
                        term.answer = new_value
                    self.controller.updateTerms([term])
                elif choice == 'd':
                    self.delete_for_manage_terms()
    
    def tag_for_manage_terms(self, term, removing=False):
        action = "add"
        if removing:
            action = "remove"
        tag = self.runTagPicker(f"Select the tag {action}: ")
        if tag is not None and tag != -1:
            if removing:
                self.controller.removeTagFromTerm(tag, term)                
            else:
                self.controller.applyTagToTerm(tag, term)
    
    def assign_category_for_manage_terms(self, term):
        category = self.runCategoryPicker("Choose a new category: ")
        if category is not None:
            self.controller.setCategoryForTerm(category, term)
        
    def delete_for_manage_terms(self, term):
        print("Are you sure you want to delete this term? This cannot be undone.")
        confirm = input("Enter 'delete' to confirm deletion: ").strip().lower()
        if confirm == "delete":
            self.controller.deleteTerm(term)
            print("Term deleted.")
        else:
            print("Deletion cancelled.")
        
    def run_export(self):
        category = self.runCategoryPicker("Select category to export:", allow_wildcard=True)
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

    def do_file_export(self, filePath, categoryName):
        if os.path.exists(filePath):
            print("ERROR: file already exists at {filePath}")
            return False

        category = None
        if not None == categoryName:
            category = self.controller.getCategoryByName(categoryName)
            if None == category:
                print('Error: no category found with name "{}"')
                return False

        self.controller.exportTermsToPath(filePath, category)
        return os.path.isfile(filePath)

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
                    self.controller.setPref_isUsingSpacedRepetition(
                        toggleSpaceRep
                    )

            elif choice == "d":
                newDist = self.run_spaced_distribution_input()
                if type(newDist) == int and newDist == -1:
                    self.inputMode = INPUT_MODE_mainmenu
                    return
                elif type(newDist) == dict and len(newDist) == 6:
                    self.controller.setPref_spacedBinDistribution(newDist)

    def run_spaced_distribution_input(self):
        binDist = self.controller.getPref_spacedBinDistribution()

        newBinDist = copy.deepcopy(binDist)

        print("\nThe bin distributions control relatively how many terms are ")
        print("selected for a drill from each 'bin', where bin 0 is all new")
        print("terms, bin 1 are the least well known, and bin 5 are the best")
        print("known.\n")

        print("Each bin value should be positive or zero. They need not add")
        print("up to any number, but will be interpreted relatively, so a")
        print("5 for one bin and 1 for another mans that questions from the")
        print("first bin will occur around 5x as often as the other bin.\n")

        print(f"Current values: {binDist}")

        for n in range(0, 6):
            newValue = input(
                f"  bin [{n}] weight (return to keep value {binDist[n]}): "
            ).strip()
            if newValue == "x":
                return -1
            if len(newValue) > 0:
                newValue = float(newValue)
                if newValue < 0:
                    print(f"ERROR: negative input {newValue}")
                    return -1

                newBinDist[n] = newValue

        return newBinDist

    def run_add(self):

        done = False
        cancelled = False

        categories = self.controller.getCategoryList()
        catLookup = {}
        for cat in categories:
            catLookup[cat.name] = cat
            
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

            category = None
            while category is None:
                category = self.runCategoryPicker()
                if category == -1:
                    cancelled = True
                    break
            
            if cancelled:
                break
            
            newTerm.category = category
            

            tags = []
            doneTagging = False
            while not doneTagging:
                nextTag = self.runTagPicker("Apply a tag (empty return to end tagging):",
                                            permit_new_tag=True,
                                            allow_none=True)
                if nextTag is None:
                    break
                if nextTag == -1:
                    cancelled = True
                    break
                tags.append(nextTag)

            if cancelled:
                break
            
            newTerm.tags = tags

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

                # TODO: sanity check newTerm - non-empty
                # Q/A, valid category and tags, etc.

                self.controller.addNewTerms([newTerm])

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
        filePath = input("Enter file path: ").strip()
        if filePath.lower() == "x":
            self.inputMode = INPUT_MODE_mainmenu
            return

        importResult = self.do_file_import(filePath)
        if importResult:
            print("Reloading deck...")
            self.controller.reloadDeck()

    def do_file_import(self, filePath):
        if not (os.path.isfile(filePath)):
            print(f"ERROR: \"{filePath}\" is not a valid file path.")
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

        #print(
        #    f"DEBUG - number of lines read from import file: {len(importLines)}"
        #)

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

            print("\ncommands: add (tag-name), delete (tag-name), clear (tag-name), x (exit)")
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
            elif command == "clear":
                if len(commandParts) < 2:
                    print(
                        "ERROR: add command should be followed by new tag name."
                    )
                else:
                    tagName = commandParts[1].strip()
                    clearTagObj = None
                    for tagObj in currentTags:
                        if tagObj.name.lower() == tagName.lower():
                            clearTagObj = tagObj

                    if None == clearTagObj:
                        print(
                            f'WARNING: tag "{tagName}" not found, nothing to clear.'
                        )
                    else:
                        print(f'Clearing terms from tag "{tagName}"...')
                        self.controller.clearTagFromTerms(clearTagObj)

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

        categoryArg = None

        foundImportCmd = False
        foundExportCmd = False

        logLevelStr = "INFO"

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
                #print(f"DEBUG got fileArg: {fileArg}")

            elif arg.startswith(f"{ARG_CATEGORY}="):
                categoryArg = arg[len(ARG_CATEGORY) + 1 :]
                #print(f"DEBUG got categoryArg: {categoryArg}")

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
            if runner.do_file_export(fileArg, categoryArg):
                return
            else:
                logging.warning("Failed to export terms.")
                sys.exit(1)

        runner.inputMode = INPUT_MODE_mainmenu
        while not runner.quit:
            runner.run_input()


if __name__ == "__main__":
    TextDrillRunner.main(sys.argv)
