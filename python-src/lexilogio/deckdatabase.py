#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Apr  9 00:01:09 2023

@author: mathaes
"""
import os
import sqlite3
from datetime import datetime
import logging

from .deck import Deck
from .term import Term
from .tag import Tag
from .category import Category


DECK_TERMS_TABLE_NAME = "deck_terms"
DECK_TERMS_COLUMN_NAMES = [
    "pkey",
    "question",
    "answer",
    "category",
    "bin",
    "reversed_bin",
    "last_drill_time",
    "has_paper_card"
]

CATEGORY_TABLE_NAME = "deck_categories"
TAG_TABLE_NAME = "deck_tags"
TAG_RELATION_TABLE_NAME = "deck_terms_tags_rel"
PREFS_TABLE_NAME = "deck_prefs"

INSERT_DEFAULT_PREFS_SQL = f"""INSERT INTO {PREFS_TABLE_NAME} (
    drill_question_count, space_repetition_bias, reverse_drill) VALUES (
    25, 1, 0);
"""

class QueryCriterion:
    CATEGORY = "category:"
    TAG = "tag:"
    QUESTION = "question:"
    ANSWER = "answer:"
    BIN = "bin:"
    REVERSEBIN = "revbin:"
    
    CRITERION_TYPES = [CATEGORY, TAG, QUESTION, ANSWER, BIN, REVERSEBIN]
    
    def __init__(self, criterionType, value):
        if not criterionType in QueryCriterion.CRITERION_TYPES:
            raise Exception(f"Unsupported criterion type: {criterionType}")
            
        self.criterionType = criterionType
        self.value = value
        
    def __repr__(self):
        return f"({self.criterionType} {self.value})"
    
    # factory methods
    def category(value):
        return QueryCriterion(QueryCriterion.CATEGORY, value)
    
    def tag(value):
        return QueryCriterion(QueryCriterion.TAG, value)
    
    def question(value):
        return QueryCriterion(QueryCriterion.QUESTION, value)
    
    def answer(value):
        return QueryCriterion(QueryCriterion.ANSWER, value)
    
    def binvalue(value):
        return QueryCriterion(QueryCriterion.BIN, value)
    
    def reversebinvalue(value):
        return QueryCriterion(QueryCriterion.REVERSEBIN, value)


class DeckDatabase:
    def fileNameForDeckName(deckName):
        deckToken = deckName.replace(" ", "_")
        return f"lexilogio_{deckToken}.db"

    def __init__(self, dbPath):
        self.dbPath = dbPath
        self.dbConnection = None

    def getFileName(self):
        return os.path.basename(self.dbPath)

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

        termToTags, tagToTerms = self.getDeckTermTagRelations(deck)
        deck.termToTags = termToTags
        deck.tagToTerms = tagToTerms

        self.readDeckPreferences(deck)
        return deck
    
    def readDeckStats(self):
        
        COUNT_SQL = f"SELECT COUNT(*) FROM {DECK_TERMS_TABLE_NAME}"
        BIN_AVG_SQL = f"SELECT AVG(bin) FROM {DECK_TERMS_TABLE_NAME}"
        RBIN_AVG_SQL = f"SELECT AVG(reversed_bin) FROM {DECK_TERMS_TABLE_NAME}"
        
        con = self.getDbConnection()
        cur = con.cursor()
        
        cur.execute(COUNT_SQL, [])
        count_result = cur.fetchone()
        if count_result is not None and len(count_result) > 0:
            count = int(count_result[0])
        else:
            count = 0
        
        cur.execute(BIN_AVG_SQL, [])
        bin_avg_result = cur.fetchone()
        if bin_avg_result[0] is not None:
            bin_avg = float(bin_avg_result[0])
        else:
            bin_avg = 0
        
        cur.execute(RBIN_AVG_SQL, [])
        rbin_avg_result = cur.fetchone()
        if rbin_avg_result[0] is not None:
            rbin_avg = float(rbin_avg_result[0])
        else:
            rbin_avg = 0
        
        result_d = {
            "count": count,
            "average": bin_avg,
            "reverse-average": rbin_avg,
            "score": count * bin_avg,
            "reverse-score": count * rbin_avg
        }
        return result_d


    def queryForAllDeckTerms(self, deck: Deck):
        self.ensureDeckTablesExist(deck)

        SELECT_SQL = f"SELECT * FROM {DECK_TERMS_TABLE_NAME}"

        con = self.getDbConnection()
        cur = con.cursor()
        cur.execute(SELECT_SQL)
        termResults = cur.fetchall()

        return DeckDatabase.queryResultsToTermArray(termResults)

    def queryForDeckTerms(
        self, deck: Deck, category: Category = None, binValues: list = None
    ):
        self.ensureDeckTablesExist(deck)

        whereClauseCount = 0
        if None != category:
            whereClauseCount += 1
        if None != binValues and len(binValues) > 0:
            whereClauseCount += 1

        if 0 == whereClauseCount:
            return self.queryForAllDeckTerms(deck)

        catWhereClauseSql = None
        catParams = []

        binWhereClauseSql = None
        binParams = []

        if not None == category:
            catWhereClauseSql = "category = ?"
            catParams.append(category.pkey)

        # TODO add isReversed para, support reversed bin query here
        if not None == binValues and len(binValues) > 0:
            binWhereClauseSql = "bin = ?"
            for n in range(1, len(binValues)):
                binWhereClauseSql += " OR bin = ?"
            binParams = binValues

        columnNamesCommaStr = ",".join(DECK_TERMS_COLUMN_NAMES)
        querySQL = (
            f"SELECT {columnNamesCommaStr} FROM {DECK_TERMS_TABLE_NAME} WHERE "
        )

        if whereClauseCount > 1:
            querySQL += "("

        clauseIndex = 0
        queryParams = []

        if catWhereClauseSql:
            querySQL += catWhereClauseSql
            queryParams.extend(catParams)
            clauseIndex += 1

        if binWhereClauseSql:
            if clauseIndex > 0:
                querySQL += ") AND ("
            querySQL += binWhereClauseSql
            queryParams.extend(binParams)
            clauseIndex += 1

        if whereClauseCount > 1:
            querySQL += ")"
        querySQL += ";"

        # print(f"DEBUG: query sql is \n{querySQL}")

        con = self.getDbConnection()
        cur = con.cursor()
        cur.execute(querySQL, queryParams)
        termResults = cur.fetchall()

        return DeckDatabase.queryResultsToTermArray(termResults)
    
    def queryByCriteria(self, deck: Deck, queryCriteriaList):
        """
        Query the database for terms based on a list of criteria.
        Multiple criteria of the same type are treated as OR clauses.
        For example if two categories are in the criteria, this query
        will match either. Criteria from different categores are treated
        as AND clauses. For instance if there is a category criterion and
        a tag criterion, the results will be terms that match both.
        """
        columnNamesCommaStr = ",".join(DECK_TERMS_COLUMN_NAMES)
        querySQL = (
            f"SELECT {columnNamesCommaStr} FROM {DECK_TERMS_TABLE_NAME}"
        )
        whereClauses = []
        whereClauseSQL = ""
        
        params = []
        
        tagCriteria = None
        
        if len(queryCriteriaList) > 0:
            
            catCriteria = list(filter(lambda cr: cr.criterionType == QueryCriterion.CATEGORY, queryCriteriaList))
            questionCriteria = list(filter(lambda cr: cr.criterionType == QueryCriterion.QUESTION, queryCriteriaList))
            answerCriteria = list(filter(lambda cr: cr.criterionType == QueryCriterion.ANSWER, queryCriteriaList))
            binCriteria = list(filter(lambda cr: cr.criterionType == QueryCriterion.BIN, queryCriteriaList))
            reverseBinCriteria = list(filter(lambda cr: cr.criterionType == QueryCriterion.REVERSEBIN, queryCriteriaList))
            
            numWhereCriteria = len(catCriteria) + len(questionCriteria) + len(answerCriteria) + len(binCriteria) + len(reverseBinCriteria)
            
            tagCriteria = list(filter(lambda cr: cr.criterionType == QueryCriterion.TAG, queryCriteriaList))

            if numWhereCriteria > 0:
                whereClauseSQL = " WHERE "
                
            if len(catCriteria) == 1:
                whereClauses.append("category = ?")
                params.append(catCriteria[0].value.pkey)
            elif len(catCriteria) > 1:
                catClause = "("
                for n in range(0, len(catCriteria)):
                    catClause += "category = ?"
                    params.append(catCriteria[n].value.pkey)
                    if n + 1 < len(catCriteria):
                        catClause += " OR "
                catClause += ")"
                whereClauses.append(catClause)
                
            if len(questionCriteria) == 1:
                whereClauses.append("question LIKE ?")
            
                params.append(questionCriteria[0].value.replace('*', '%'))
            elif len(questionCriteria) > 1:
                questionClause = "("
                for n in range(0, len(questionCriteria)):
                    questionClause += "question LIKE ?"
                    params.append(questionCriteria[n].value.replace('*', '%'))
                    if n + 1 < len(questionCriteria):
                        questionClause += " OR "
                questionClause += ")"
                whereClauses.append(questionClause)
                
            if len(answerCriteria) == 1:
                whereClauses.append("answer LIKE ?")
            
                params.append(answerCriteria[0].value.replace('*', '%'))
            elif len(answerCriteria) > 1:
                answerClause = "("
                for n in range(0, len(answerClause)):
                    answerClause += "answer LIKE ?"
                    params.append(answerCriteria[n].value.replace('*', '%'))
                    if n + 1 < len(answerCriteria):
                        answerClause += " OR "
                answerClause += ")"
                whereClauses.append(answerClause)
                
            if len(binCriteria) == 1:
                whereClauses.append("bin = ?")
                params.append(int(binCriteria[0].value))
            elif len(binCriteria) > 1:
                binClause = "("
                for n in range(0, len(binCriteria)):
                    binClause += "bin = ?"
                    params.append(int(binCriteria[n].value))
                    if n + 1 < len(binCriteria):
                        binClause += " OR "
                binClause += ")"
                whereClauses.append(binClause)
                
            if len(reverseBinCriteria) == 1:
                whereClauses.append("reversed_bin = ?")
                params.append(int(reverseBinCriteria[0].value))
            elif len(reverseBinCriteria) > 1:
                revbinClause = "("
                for n in range(0, len(reverseBinCriteria)):
                    revbinClause += "reversed_bin = ?"
                    params.append(int(reverseBinCriteria[n].value))
                    if n + 1 < len(reverseBinCriteria):
                        revbinClause += " OR "
                revbinClause += ")"
                whereClauses.append(revbinClause)
            
                
            print(f"DEBUG: whereClauses: {whereClauses}")
            # TODO: tags - as JOIN clause, or just post-process filtering step?
            if len(whereClauses) == 1:
                whereClauseSQL += whereClauses[0]
            else: 
                for wcIndex in range(0, len(whereClauses)):
                    whereClauseSQL += f"({whereClauses[wcIndex]})"
                    if wcIndex + 1 < len(whereClauses):
                        whereClauseSQL += " AND "
                    
        
        if len(whereClauseSQL) > 0:
            querySQL += whereClauseSQL
        querySQL += ";"
            
        con = self.getDbConnection()
        cur = con.cursor()
        
        print(f"DEBUG - executing SQL: {querySQL}")
        
        termResults = None
        if len(params) == 0:
            cur.execute(querySQL)
            termResults = cur.fetchall()
        else:
            print(f"DEBUG params:\n  {params}")
            cur.execute(querySQL, params)
            termResults = cur.fetchall()
        if None == termResults or len(termResults) == 0:
            return []
        
        results = DeckDatabase.queryResultsToTermArray(termResults)
        
        # TODO - now we filter by tags - probably more expensive than
        #  join but less complex to implement dynamically
        if tagCriteria and len(tagCriteria) > 0:
            taggedTermPKs = []
            for tagCriterion in tagCriteria:
                tag = tagCriterion.value
                taggedTerms = deck.getTermsWithTag(tag)
                taggedTermPKs.extend(list(map(lambda t: t.pkey, taggedTerms)))
                
            results = list(filter(lambda tt: tt.pkey in taggedTermPKs, results))
                
        return results
        
    def queryResultsToTermArray(results):
        terms = []
        for row in results:
            if not len(row) == len(DECK_TERMS_COLUMN_NAMES):
                raise Exception(
                    f"Unexpected row results for Term object: {row}"
                )

            term = Term()
            # columns should be: pkey, question, answer, category, bin, tags
            term.pkey = int(row[0])
            term.question = row[1]
            term.answer = row[2]
            term.category = row[3]
            term.bin = int(row[4])
            term.reversedBin = int(row[5])
            term.lastDrillTime = row[6]

            terms.append(term)

        return terms

    def insertTerms(self, deck: Deck, termList: list):
        self.ensureDeckTablesExist(deck)

        # Note that terms are always inserted with last_drill_time NULL.
        # If we want to support importing terms from an active database and
        # preserving drill time a new method will be required, esp. if we
        # want to use last_drill_time to reconcile any conflicts.

        insertSQL = f"""INSERT INTO {DECK_TERMS_TABLE_NAME} (question, answer, category, bin, reversed_bin) 
    VALUES (?, ?, ?, ?, ?);
"""
        
        tagRelateSQL = f"""INSERT INTO {TAG_RELATION_TABLE_NAME} (term, tag) VALUES (?, ?);"""

        con = self.getDbConnection()
        cur = con.cursor()
        

        for term in termList:
            category_pkey = term.category
            if type(term.category) is Category:
                category_pkey = term.category.pkey
                
            termParams = [
                (term.question),
                (term.answer),
                (category_pkey),
                (term.bin),
                (term.reversedBin),
            ]

            cur.execute(insertSQL, termParams)
            
            term.pkey = cur.lastrowid
            if term.tags is not None:
                for tag in term.tags:
                    term_tag_params = [term.pkey, tag.pkey]
                    cur.execute(tagRelateSQL, term_tag_params)

        con.commit()

    def updateTerms(self, deck: Deck, termList: list):
        self.ensureDeckTablesExist(deck)

        con = self.getDbConnection()
        cur = con.cursor()

        for term in termList:
            timeSetter = ""
        if not None == term.lastDrillTime:
            timeSetter = ", last_drill_time = ?"

        updateSql = f"""UPDATE {DECK_TERMS_TABLE_NAME} 
SET question = ?, answer = ?, category = ?, bin = ?, reversed_bin = ? {timeSetter}
WHERE pkey = ?;
"""

        params = [
            (term.question),
            (term.answer),
            (term.category),
            (term.bin),
            (term.reversedBin),
        ]

        if not None == term.lastDrillTime:
            params.append((term.lastDrillTime))

        params.append((term.pkey))

        cur.execute(updateSql, params)

        con.commit()
        
    def udpateTermCategory(self, deck: Deck, catpk, termpk):
        con = self.getDbConnection()
        cur = con.cursor()
        updateSQL = f"UPDATE {DECK_TERMS_TABLE_NAME} SET category = ? WHERE pkey = ?;"
        params = [(catpk), (termpk),]
        cur.execute(updateSQL, params)
        con.commit()

    def deleteTerm(self, deck: Deck, term: Term):
        self.ensureDeckTablesExist(deck)

        con = self.getDbConnection()
        cur = con.cursor()
        
        deleteSql = f"DELETE from {DECK_TERMS_TABLE_NAME} WHERE pkey = ?;"
        params = [(term.pkey),]
        cur.execute(deleteSql, params)
        con.commit()
        
    def updateTermBins(
        self, deck: Deck, termList: list, isReversedDrill=False
    ):
        self.ensureDeckTablesExist(deck)

        UPDATE_BIN_SQL = f"UPDATE {DECK_TERMS_TABLE_NAME} SET bin = ?, last_drill_time = ? WHERE pkey = ?;"

        UPDATE_REVERSED_BIN_SQL = f"""UPDATE {DECK_TERMS_TABLE_NAME} 
SET reversed_bin = ?, last_drill_time = ? WHERE pkey = ?;"""

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

            logging.debug(
                f"executing updateSql {updateSql} with params {params}"
            )
            cur.execute(updateSql, params)

        con.commit()

    def getDeckCategories(self, deck: Deck):
        self.ensureDeckTablesExist(deck)

        querySql = f"SELECT pkey, category FROM {CATEGORY_TABLE_NAME};"

        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(querySql)
        rows = cur.fetchall()

        categories = []
        for catRow in rows:
            catPK = int(catRow[0])
            catName = str(catRow[1])
            cat = Category(name=catName, pkey=catPK)
            categories.append(cat)

        return categories

    def insertDeckCategory(self, deck: Deck, categoryName):
        self.ensureDeckTablesExist(deck)

        querySql = f"INSERT INTO {CATEGORY_TABLE_NAME} (category) VALUES (?);"

        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(
            querySql,
            [
                (categoryName),
            ],
        )
        newCatPK = cur.lastrowid

        con.commit()

        newCat = Category(name=categoryName, pkey=newCatPK)
        return newCat

    def deleteDeckCategory(self, deck: Deck, category):
        self.ensureDeckTablesExist(deck)

        # first clear the category from any assigned entries
        updateSQL = f"UPDATE {CATEGORY_TABLE_NAME} SET category = NULL WHERE category = ?;"
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

        querySql = f"SELECT pkey, tag FROM {TAG_TABLE_NAME};"

        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(querySql)
        rows = cur.fetchall()

        tags = []
        for tagRow in rows:
            tagPK = int(tagRow[0])
            tagName = str(tagRow[1])
            tag = Tag(name=tagName, pkey=tagPK)
            tags.append(tag)

        return tags

    def getDeckTermTagRelations(self, deck: Deck):
        querySql = f"SELECT term, tag FROM {TAG_RELATION_TABLE_NAME};"

        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(querySql)
        rows = cur.fetchall()

        termToTags = {}
        tagToTerms = {}

        for relRow in rows:
            termPK = relRow[0]
            tagPK = relRow[1]

            if termPK in termToTags:
                termToTags[termPK].append(tagPK)
            else:
                termToTags[termPK] = [tagPK]

            if tagPK in tagToTerms:
                tagToTerms[tagPK].append(termPK)
            else:
                tagToTerms[tagPK] = [termPK]

        return (termToTags, tagToTerms)

    def applyTagToTerm(self, deck: Deck, term: Term, tag: Tag):
        if None == term.pkey or None == tag.pkey:
            raise Exception(
                "applyTagToTerm needs objects with database primary keys set."
            )

        insertSQL = (
            f"INSERT INTO {TAG_RELATION_TABLE_NAME} (term, tag) VALUES (?, ?);"
        )
        params = [
            (term.pkey),
            (tag.pkey),
        ]

        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(insertSQL, params)
        con.commit()

        if term.pkey in deck.termToTags:
            deck.termToTags[term.pkey].append(tag.pkey)
        else:
            deck.termToTags[term.pkey] = [tag.pkey]

        if tag.pkey in deck.tagToTerms:
            deck.tagToTerms[tag.pkey].append(term.pkey)
        else:
            deck.tagToTerms[tag.pkey] = [term.pkey]

    def removeTagFromTerm(self, deck: Deck, tag: Tag, term: Term):
        deleteSQL = f"DELETE FROM {TAG_RELATION_TABLE_NAME} WHERE (term = ? AND tag = ?);"
        params = [(term.pkey), (tag.pkey),]
        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(deleteSQL, params)
        con.commit()
        
    def clearTagFromAllTerms(self, deck: Deck, tag: Tag):
        clearSQL = f"DELETE FROM {TAG_RELATION_TABLE_NAME} WHERE (tag=?);"
        params = [(tag.pkey),]
        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(clearSQL, params)
        con.commit()
        
    def insertDeckTag(self, deck: Deck, tag_name):
        self.ensureDeckTablesExist(deck)

        newTag = Tag(name=tag_name)

        querySql = f"INSERT INTO {TAG_TABLE_NAME} (tag) VALUES (?);"

        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(querySql, [tag_name])

        newTag.pkey = int(cur.lastrowid)

        con.commit()

        deck.tags.append(newTag)

        return newTag

    def deleteDeckTag(self, deck: Deck, tag: Tag):
        self.ensureDeckTablesExist(deck)

        if None == tag.pkey:
            raise Exception("Tag object missing pkey value.")

        # first delete the relations
        deleteTagRelationSQL = (
            f"DELETE FROM {TAG_RELATION_TABLE_NAME} WHERE tag = ?;"
        )
        deleteTagSQL = f"DELETE FROM {TAG_TABLE_NAME} WHERE pkey = ?;"

        con = self.getDbConnection()
        cur = con.cursor()

        cur.execute(deleteTagRelationSQL, [tag.pkey])
        cur.execute(deleteTagSQL, [tag.pkey])
        con.commit()

        # note, caller should reload deck

    def readDeckPreferences(self, deck: Deck):
        self.ensureDeckTablesExist(deck)

        READ_SQL = f"""SELECT 
        bin0_weight,
        bin1_weight,
        bin2_weight,
        bin3_weight,
        bin4_weight,
        bin5_weight,
        drill_question_count, 
        space_repetition_bias, 
        reverse_drill
        FROM {PREFS_TABLE_NAME};
        """

        con = self.getDbConnection()
        cur = con.cursor()

        resultRow = cur.execute(READ_SQL).fetchone()
        if None == resultRow:
            # write default prefs
            cur.execute(INSERT_DEFAULT_PREFS_SQL)
            con.commit()
            cur = con.cursor()
            resultRow = cur.execute(READ_SQL).fetchone()

        binDist = {}
        for n in range(0, 6):
            binDist[n] = float(resultRow[n])
        qCount = resultRow[6]
        # print (f"DEBUG: qCount = {qCount}")
        useSR = resultRow[7]
        # print (f"DEBUG: useSR = {useSR}")
        reversedDrill = resultRow[8]

        deck.prefs = {
            Deck.PREFSKEY_QUESTION_COUNT: int(qCount),
            Deck.PREFSKEY_SPACED_REPETITION: int(useSR) != 0,
            Deck.PREFSKEY_REVERSED_DRILL: int(reversedDrill) != 0,
            Deck.PREFSKEY_SPACED_BIN_DISTRIBUTION: binDist,
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

        binDist = deck.prefs[Deck.PREFSKEY_SPACED_BIN_DISTRIBUTION]

        DELETE_OLD_ENTRY_SQL = f"DELETE FROM {PREFS_TABLE_NAME};"

        con = self.getDbConnection()
        cur = con.cursor()
        cur.execute(DELETE_OLD_ENTRY_SQL)
        con.commit()

        WRITE_SQL = f"""INSERT INTO {PREFS_TABLE_NAME} (
        bin0_weight, bin1_weight, bin2_weight, bin3_weight, bin4_weight, bin5_weight,
    drill_question_count, space_repetition_bias, reverse_drill) VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?, ?
);"""
        cur = con.cursor()
        cur.execute(
            WRITE_SQL,
            [
                (binDist[0]),
                (binDist[1]),
                (binDist[2]),
                (binDist[3]),
                (binDist[4]),
                (binDist[5]),
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
                raise Exception(
                    f"Could not find or create table for deck {deck.name}"
                )

    def checkDeckTableExists(self, deck: Deck):
        CHECK_SQL = "SELECT name FROM sqlite_master;"

        con = self.getDbConnection()
        cur = con.cursor()
        cur.execute(CHECK_SQL)

        nameRows = cur.execute(CHECK_SQL).fetchall()
        names = [r[0] for r in nameRows if len(r) > 0]
        # print(f"DEBUG - sqlite_master table names: {names}")

        return DECK_TERMS_TABLE_NAME in names

    def createDeckTables(self, deck: Deck):
        con = self.getDbConnection()
        cur = con.cursor()

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

        CREATE_SQL_terms = f"""CREATE TABLE IF NOT EXISTS {DECK_TERMS_TABLE_NAME} (
    pkey INTEGER PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category INT NULL,
    bin INTEGER DEFAULT 0 NOT NULL,
    reversed_bin INTEGER DEFAULT 0 NOT NULL,
    last_drill_time TEXT DEFAULT NULL,
    has_paper_card INT DEFAULT 0,
    FOREIGN KEY(category) REFERENCES {CATEGORY_TABLE_NAME}(pkey)
);
"""

        cur.execute(CREATE_SQL_terms)

        CREATE_SQL_tagrelation = f"""CREATE TABLE IF NOT EXISTS {TAG_RELATION_TABLE_NAME} (
    pkey INTEGER PRIMARY KEY,
    term INTEGER NOT NULL,
    tag INTEGER NOT NULL,
    FOREIGN KEY(term) REFERENCES {DECK_TERMS_TABLE_NAME}(pkey),
    FOREIGN KEY(tag) REFERENCES {TAG_TABLE_NAME}(pkey)
);
"""
        cur.execute(CREATE_SQL_tagrelation)

        CREATE_SQL_prefs = f"""CREATE TABLE IF NOT EXISTS {PREFS_TABLE_NAME} (
    pkey INTEGER PRIMARY KEY,
    drill_question_count INTEGER DEFAULT 25 NOT NULL,
    space_repetition_bias INTEGER DEFAULT 1 NOT NULL,
    reverse_drill INTEGER DEFAULT 0 NOT NULL,
    category TEXT DEFAULT NULL,
    bin0_weight REAL DEFAULT 0.36,
    bin1_weight REAL DEFAULT 0.25,
    bin2_weight REAL DEFAULT 0.16,
    bin3_weight REAL DEFAULT 0.11,
    bin4_weight REAL DEFAULT 0.07,
    bin5_weight REAL DEFAULT 0.05
);
"""
        cur.execute(CREATE_SQL_prefs)

        # Also insert default prefs row (category NULL)
        cur.execute(INSERT_DEFAULT_PREFS_SQL)

        con.commit()
