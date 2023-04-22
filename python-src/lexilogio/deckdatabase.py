#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Apr  9 00:01:09 2023

@author: mathaes
"""

from .deck import Deck
from .term import Term

import sqlite3
from datetime import datetime


DECK_TABLE_NAME = "deck_terms"
CATEGORY_TABLE_NAME = "deck_categories"
TAG_TABLE_NAME = "deck_tags"
PREFS_TABLE_NAME = "deck_prefs"

INSERT_DEFAULT_PREFS_SQL = f"""INSERT INTO {PREFS_TABLE_NAME} (
    drill_question_count, space_repetition_bias, reverse_drill) VALUES (
    25, 1, 0);
"""


class DeckDatabase:
    def fileNameForDeckName(deckName):
        deckToken = deckName.replace(" ", "_")
        return f"lexilogio_{deckToken}.db"

    def __init__(self, dbPath):
        self.dbPath = dbPath
        self.dbConnection = None

    def getDbConnection(self):
        if None == self.dbConnection:
            self.dbConnection = sqlite3.connect(self.dbPath)
        return self.dbConnection

    def loadDeck(self, deckName):
        deck = Deck(deckName)
        self.ensureDeckTablesExist(deck)
        deck.terms = self.queryForAllDeckTerms(deck)
        deck.categories = self.getDeckCategories(deck)
        deck.tags = self.getDeckTags(deck)
        self.readDeckPreferences(deck)
        return deck

    def queryForAllDeckTerms(self, deck: Deck):
        self.ensureDeckTablesExist(deck)

        SELECT_SQL = f"SELECT * FROM {DECK_TABLE_NAME}"

        con = self.getDbConnection()
        cur = con.cursor()
        cur.execute(SELECT_SQL)
        termResults = cur.fetchall()

        return DeckDatabase.queryResultsToTermArray(termResults)

    def queryForDeckTerms(
        self,
        deck: Deck,
        category: str = None,
        binValues: list = None,
        tags: list = None,
    ):
        self.ensureDeckTablesExist(deck)

        whereClauseCount = 0
        if None != category:
            whereClauseCount += 1
        if None != binValues and len(binValues) > 0:
            whereClauseCount += 1
        if None != tags and len(tags) > 0:
            whereClauseCount += 1

        if 0 == whereClauseCount:
            return self.queryForAllDeckTerms(deck)

        catWhereClauseSql = None
        catParams = []

        binWhereClauseSql = None
        binParams = []

        tagsWhereClauseSql = None
        tagParams = []

        if not None == category:
            catWhereClauseSql = "category = ?"
            catParams.append(category)

        # TODO add isReversed para, support reversed bin query here
        if not None == binValues and len(binValues) > 0:
            binWhereClauseSql = "bin = ?"
            for n in range(1, len(binValues)):
                binWhereClauseSql += " OR bin = ?"
            binParams = binValues

        if not None == tags and len(tags) > 0:
            tagsWhereClauseSql = ""
            for n in range(0, len(tags)):
                if n > 0:
                    tagsWhereClauseSql += " OR "
                tagsWhereClauseSql += "tags LIKE ?"
                tagParams.append(("%" + tags[n] + "%"))

        querySQL = f"SELECT * FROM {DECK_TABLE_NAME} WHERE "

        if whereClauseCount > 1:
            querySQL += "("

        clauseIndex = 0
        queryParams = []

        if catWhereClauseSql:
            querySQL += catWhereClauseSql
            queryParams.exrend(catParams)
            clauseIndex += 1

        if binWhereClauseSql:
            if clauseIndex > 0:
                querySQL += ") AND ("
            querySQL += binWhereClauseSql
            queryParams.extend(binParams)
            clauseIndex += 1

        if tagsWhereClauseSql:
            if clauseIndex > 0:
                querySQL += ") AND ("
            querySQL += tagsWhereClauseSql
            queryParams.extend(tagParams)

        if whereClauseCount > 1:
            querySQL += ")"
        querySQL += ";"

        print(f"DEBUG: query sql is \n{querySQL}")

        con = self.getDbConnection()
        cur = con.cursor()
        cur.execute(querySQL, queryParams)
        termResults = cur.fetchall()

        return DeckDatabase.queryResultsToTermArray(termResults)

    def queryResultsToTermArray(results):
        terms = []
        for row in results:
            if not len(row) == 8:
                raise Exception(f"Unexpected row results for Term object: {row}")

            term = Term()
            # columns should be: pkey, question, answer, category, bin, tags
            term.pkey = int(row[0])
            term.question = row[1]
            term.answer = row[2]
            term.category = row[3]
            term.bin = int(row[4])
            term.reversedBin = int(row[5])
            term.tags = str(row[6]).split(",")
            term.lastDrillTime = row[7]

            terms.append(term)

        return terms

    def insertTerms(self, deck: Deck, termList: list):
        self.ensureDeckTablesExist(deck)

        # Note that terms are always inserted with last_drill_time NULL.
        # If we want to support importing terms from an active database and
        # preserving drill time a new method will be required, esp. if we
        # want to use last_drill_time to reconcile any conflicts.

        insertSQL = f"""INSERT INTO {DECK_TABLE_NAME} (question, answer, category, bin, reversed_bin, tags) 
    VALUES (?, ?, ?, ?, ?, ?);
"""

        con = self.getDbConnection()
        cur = con.cursor()

        for term in termList:
            tagStr = term.getTagStr()

            termParams = [
                (term.question),
                (term.answer),
                (term.category),
                (term.bin),
                (term.reversedBin),
                (tagStr),
            ]

            cur.execute(insertSQL, termParams)

        con.commit()

    def updateTerms(self, deck: Deck, termList: list):
        self.ensureDeckTablesExist(deck)

        con = self.getDbConnection()
        cur = con.cursor()

        for term in termList:
            timeSetter = ""
        if not None == term.lastDrillTime:
            timeSetter = ", last_drill_time = ?"

            updateSql = f""""UDPATE {DECK_TABLE_NAME} 
SET question = ?, answer = ?, category = ?, bin = ?, reversed_bin = ?, tags = ? {timeSetter}
WHERE pkey = ?;
"""

            tagStr = ""
            if len(term.tags) > 0:
                tagStr = ",".join(term.tags)

            params = [
                (term.question),
                (term.answer),
                (term.category),
                (term.bin),
                (term.reversedBin),
                (tagStr),
            ]

            if not None == term.lastDrillTime:
                params.append((term.lastDrillTime))

            params.append((term.pkey))

            cur.execute(updateSql, params)

        con.commit()

    def updateTermBins(self, deck: Deck, termList: list, isReversedDrill=False):
        self.ensureDeckTablesExist(deck)

        UPDATE_BIN_SQL = (
            f"UPDATE {DECK_TABLE_NAME} SET bin = ?, last_drill_time = ? WHERE pkey = ?;"
        )

        UPDATE_REVERSED_BIN_SQL = f"UPDATE {DECK_TABLE_NAME} SET reversed_bin = ?, last_drill_time = ? WHERE pkey = ?;"

        updateSql = UPDATE_BIN_SQL
        if isReversedDrill:
            updateSql = UPDATE_REVERSED_BIN_SQL

        currentTime = datetime.utcnow().isoformat()

        con = self.getDbConnection()
        cur = con.cursor()

        params = None

        for term in termList:
            if isReversedDrill:
                params = [(term.reversedBin)]
            else:
                params = [(term.bin)]

            if term.lastDrillTime == None:
                term.lastDrillTime = currentTime

            params.append((term.lastDrillTime))

            params.append((term.pkey))

            print(f"DEBUG - executing updateSql {updateSql} with params {params}")
            cur.execute(updateSql, params)

        con.commit()

    def updateTermTags(self, deck: Deck, termList: list):
        updateTagSql = f"UPDATE {DECK_TABLE_NAME} SET tags = ? WHERE pkey = ?;"

        con = self.getDbConnection()
        cur = con.cursor()

        for term in termList:
            params = [
                (term.getTagStr()),
                (term.pkey),
            ]
            cur.execute(updateTagSql, params)

        con.commit()

    def getDeckCategories(self, deck: Deck):
        self.ensureDeckTablesExist(deck)

        querySql = f"SELECT category FROM {CATEGORY_TABLE_NAME};"

        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(querySql)
        rows = cur.fetchall()

        categories = [cat[0] for cat in rows if len(cat) > 0]
        return categories

    def insertDeckCategory(self, deck: Deck, category):
        self.ensureDeckTablesExist(deck)

        querySql = f"INSERT INTO {CATEGORY_TABLE_NAME} (category) VALUES (?);"

        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(
            querySql,
            [
                (category),
            ],
        )
        con.commit()

        deck.categories.append(category)

    def deleteDeckCategory(self, deck: Deck, category):
        self.ensureDeckTablesExist(deck)

        # first clear the category from any assigned entries
        updateSQL = (
            f"UPDATE {CATEGORY_TABLE_NAME} SET category = NULL WHERE category = ?;"
        )
        deleteSql = f"DELETE FROM {CATEGORY_TABLE_NAME} WHERE category = ?;"

        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(
            updateSQL,
            [
                (category),
            ],
        )
        cur.execute(
            deleteSql,
            [
                (category),
            ],
        )
        con.commit()

        if category in deck.categories:
            deck.categories.remove(category)

    def getDeckTags(self, deck: Deck):
        self.ensureDeckTablesExist(deck)

        querySql = f"SELECT tag FROM {TAG_TABLE_NAME};"

        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(querySql)
        rows = cur.fetchall()

        tags = [tag[0] for tag in rows if len(tag) > 0]
        return tags

    def insertDeckTag(self, deck: Deck, tag):
        self.ensureDeckTablesExist(deck)

        querySql = f"INSERT INTO {TAG_TABLE_NAME} (tag) VALUES (?);"

        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(
            querySql,
            [
                (tag),
            ],
        )
        con.commit()

        if not tag in deck.tags:
            deck.tags.append(tag)

    def deleteDeckTag(self, deck: Deck, tag):
        self.ensureDeckTablesExist(deck)

        taggedTerms = self.queryForDeckTerms(deck=deck, tags=[tag])
        updateTerms = []
        for term in taggedTerms:
            if tag in term.tags:
                term.tags.remove(tag)
                updateTerms.append(term)

        if len(updateTerms) > 0:
            self.updateTermTags(deck, updateTerms)

        querySql = f"DELETE FROM {TAG_TABLE_NAME} WHERE tag = ?;"

        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(
            querySql,
            [
                (tag),
            ],
        )
        con.commit()

        if tag in deck.tags:
            deck.tags.remove(tag)

    def readDeckPreferences(self, deck: Deck):
        self.ensureDeckTablesExist(deck)

        READ_SQL = f"SELECT drill_question_count, space_repetition_bias, reverse_drill FROM {PREFS_TABLE_NAME};"
        con = self.getDbConnection()
        cur = con.cursor()

        resultRow = cur.execute(READ_SQL).fetchone()
        if None == resultRow:
            # write default prefs
            cur.execute(INSERT_DEFAULT_PREFS_SQL)
            con.commit()
            cur = con.cursor()
            resultRow = cur.execute(READ_SQL).fetchone()

        qCount = resultRow[0]
        # print (f"DEBUG: qCount = {qCount}")
        useSR = resultRow[1]
        # print (f"DEBUG: useSR = {useSR}")
        reversedDrill = resultRow[2]

        deck.prefs = {
            Deck.PREFSKEY_QUESTION_COUNT: int(qCount),
            Deck.PREFSKEY_SPACED_REPETITION: int(useSR) != 0,
            Deck.PREFSKEY_REVERSED_DRILL: int(reversedDrill) != 0,
        }
        return deck.prefs

    def writeDeckPreferences(self, deck: Deck):
        self.ensureDeckTablesExist(deck)

        qCount = deck.prefs[Deck.PREFSKEY_QUESTION_COUNT]
        useSR = deck.prefs[Deck.PREFSKEY_SPACED_REPETITION]
        useSRintValue = 1
        if not useSR:
            useSRintValue = 0
        reversedDrill = deck.prefs[Deck.PREFSKEY_REVERSED_DRILL]
        reversedDrillIntValue = 0
        if reversedDrill:
            reversedDrillIntValue = 1

        DELETE_OLD_ENTRY_SQL = f"DELETE FROM {PREFS_TABLE_NAME};"

        con = self.getDbConnection()
        cur = con.cursor()
        cur.execute(DELETE_OLD_ENTRY_SQL)
        con.commit()

        WRITE_SQL = f"""INSERT INTO {PREFS_TABLE_NAME} (
    drill_question_count, space_repetition_bias, reverse_drill) VALUES (
    ?, ?, ?
);"""
        cur = con.cursor()
        cur.execute(
            WRITE_SQL,
            [
                (qCount),
                (useSRintValue),
                (reversedDrillIntValue),
            ],
        )
        con.commit()

    def ensureDeckTablesExist(self, deck: Deck):
        if not self.checkDeckTableExists(deck):
            self.createDeckTables(deck)
            if not self.checkDeckTableExists(deck):
                raise Exception(f"Could not find or create table for deck {deck.name}")

    def checkDeckTableExists(self, deck: Deck):
        CHECK_SQL = "SELECT name FROM sqlite_master;"

        con = self.getDbConnection()
        cur = con.cursor()
        cur.execute(CHECK_SQL)

        nameRows = cur.execute(CHECK_SQL).fetchall()
        names = [r[0] for r in nameRows if len(r) > 0]
        # print(f"DEBUG - sqlite_master table names: {names}")

        return DECK_TABLE_NAME in names

    def createDeckTables(self, deck: Deck):

        CREATE_SQL_terms = f"""CREATE TABLE IF NOT EXISTS {DECK_TABLE_NAME} (
    pkey INTEGER PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category INT NULL,
    bin INTEGER DEFAULT 0 NOT NULL,
    reversed_bin INTEGER DEFAULT 0 NOT NULL,
    tags TEXT DEFAULT "" NOT NULL,
    last_drill_time TEXT DEFAULT NULL
);
"""
        con = self.getDbConnection()
        cur = con.cursor()
        cur.execute(CREATE_SQL_terms)

        CREATE_SQL_categories = f"""CREATE TABLE IF NOT EXISTS {CATEGORY_TABLE_NAME} (
    pkey INTEGER PRIMARY KEY,
    category TEXT NOT NULL
);
"""
        cur.execute(CREATE_SQL_categories)

        CREATE_SQL_tags = f"""CREATE TABLE IF NOT EXISTS {TAG_TABLE_NAME} (
    pkey INTEGER PRIMARY KEY,
    tag TEXT NOT NULL
);
"""
        cur.execute(CREATE_SQL_tags)

        CREATE_SQL_prefs = f"""CREATE TABLE IF NOT EXISTS {PREFS_TABLE_NAME} (
    pkey INTEGER PRIMARY KEY,
    drill_question_count INTEGER DEFAULT 25 NOT NULL,
    space_repetition_bias INTEGER DEFAULT 1 NOT NULL,
    reverse_drill INTEGER DEFAULT 0 NOT NULL,
    category TEXT DEFAULT NULL
);
"""
        cur.execute(CREATE_SQL_prefs)

        # Also insert default prefs row (category NULL)
        cur.execute(INSERT_DEFAULT_PREFS_SQL)

        con.commit()
