#!/usr/bin/python
import io
import math
import sys
import getopt
import pickle
import heapq

from nltk.stem.porter import PorterStemmer
from nltk.corpus import wordnet
from tokenize_word import *
from ast import literal_eval

positional_dictionary = {}
dictionary = {}
doc_freq = {}
K = 10


##------------------ I/O -------------------##
def load_query(queries_file):
    """
    load queries file
    return a list of expression tokens
    """
    queries = []
    f = open(queries_file, "r")
    line = f.readline()
    f.close()
    return line.rstrip().split(" ")


def expand_query(query):
    terms = remove_Stopwords(query)
    synonyms = []
    count = 0
    for x in terms:
        for syn in wordnet.synsets(x):
            for l in syn.lemmas():
                if (count < 3):
                    if l.name() not in synonyms:
                        synonyms.append(l.name())
                        count += 1
        count = 0
    expanded_query = synonyms + terms
    return expanded_query


def load_positional_dictionary(dic_file):
    """
    Reconstruct postional dictionary from file
    """
    constructed_dic = pickle.load(open('positional_' + dic_file, "rb"))
    return constructed_dic


def load_dictionary(dic_file):
    """
    Reconstruct non-postional dictionary from file
    """
    constructed_dic = pickle.load(open(dic_file, "rb"))
    return constructed_dic


def load_doc_freq():
    """
    Reconstruct Document frequency dict for all terms
    """
    df = pickle.load(open('doc_freq', "rb"))
    return df


def read_positional_posting_list(offset):
    """
    Read postional posting list of a particular token
    """
    postings = open('positional_' + postings_file, 'r')
    postings.seek(int(offset))
    posting_list = postings.readline().rstrip().split(' ')

    positions = open('positions.txt', 'r')

    posting_list_iter = iter(posting_list)
    doc_to_positions = {}
    for i in range(int(len(posting_list) / 2)): #TODO: ask about this
        doc_id = next(posting_list_iter)
        pointer = next(posting_list_iter)
        positions.seek(int(pointer))
        position_list = positions.readline().rstrip().split(' ')
        doc_to_positions[doc_id] = position_list
    postings.close()
    positions.close()
    return doc_to_positions


def read_normal_posting_list(offset):
    """
    Read posting list of a particular token
    """
    f = open(postings_file, 'r')
    f.seek(int(offset))
    content = f.readline()
    return literal_eval(content.rstrip())


##------------------ Auxillary -------------------##
def and_operation(p1, p2):
    """
    merge 2 posting lists with AND operation
    """
    i1 = 0
    i2 = 0
    merged_list = []
    while i1 < len(p1) and i2 < len(p2):
        if p1[i1] == p2[i2]:
            merged_list.append(p1[i1])
            i1 += 1
            i2 += 1
        elif int(p1[i1]) > int(p2[i2]):
            i2 += 1
        else:
            i1 += 1
    return merged_list


def has_phrase_2(list_1, list_2):
    # perform 'merge'
    l_index = 0  # current index in left_operand
    r_index = 0  # current index in right_operand

    while (l_index < len(list_1) and r_index < len(list_2)):
        l_item = list_1[l_index]  # current item in left_operand
        r_item = list_2[r_index]  # current item in right_operand

        # case 1: if match
        if (int(l_item) == int(r_item) - 1):
            return True

        # case 2: if left item is more than right item
        elif (int(l_item) > int(r_item)):
                r_index += 1

        # case 3: if left item is less than right item
        else:
                l_index += 1
    return False


def has_phrase_3(list_1, list_2, list_3):
    # perform 'merge'
    l_index = 0  # current index in left_operand
    r_index = 0  # current index in right_operand

    intermediate_list = []

    while (l_index < len(list_1) and r_index < len(list_2)):
        l_item = list_1[l_index]  # current item in left_operand
        r_item = list_2[r_index]  # current item in right_operand

        # case 1: if match
        if (int(l_item) == int(r_item) - 1):
            intermediate_list.append(r_item)
            l_index += 1            # advance left index
            r_index += 1            # advance right index

        # case 2: if left item is more than right item
        elif (int(l_item) > int(r_item)):
            r_index += 1

        # case 3: if left item is less than right item
        else:
            l_index += 1

    if not intermediate_list:
        return False
    else:
        return has_phrase_2(intermediate_list, list_3)


def get_doc_for_phrase(query_terms):
    all_posting_lists = []
    output = ''
    for term in query_terms:
        if term in positional_dictionary:
            offset_in_postings = positional_dictionary[term][1]
            all_posting_lists.append(read_positional_posting_list(offset_in_postings))

    first_posting_list = all_posting_lists[0]
    merged_posting_list = {}
    results = []

    if len(all_posting_lists) == 3:
        second_posting_list = all_posting_lists[1]
        third_posting_list = all_posting_lists[2]

        for doc_id in first_posting_list:
            if doc_id in second_posting_list and doc_id in third_posting_list:
                merged_posting_list[doc_id] = [first_posting_list[doc_id], second_posting_list[doc_id], third_posting_list[doc_id]]

                if has_phrase_3(first_posting_list[doc_id], second_posting_list[doc_id], third_posting_list[doc_id]):
                    results.append(doc_id)


    if len(all_posting_lists) == 2:
        second_posting_list = all_posting_lists[1]

        for doc_id in first_posting_list:
            if doc_id in second_posting_list:
                merged_posting_list[doc_id] = [first_posting_list[doc_id], second_posting_list[doc_id]]

                if has_phrase_2(first_posting_list[doc_id], second_posting_list[doc_id]):
                    results.append(doc_id)

    if len(all_posting_lists) == 1:
        for doc_id in first_posting_list:
            results.append(doc_id)
    return results


##------------------ Query Processing -------------------##
def process_boolean_query(expression_tokens):
    """
    process boolean query (query with AND operator)
    """

    print("PROCESSING BOOLEAN")
    result = ''
    phrases = []
    postings_list = []
    current_phrase = []

    for token in expression_tokens:
        if token != 'AND':
            # Remove '"' from phrase
            if token[0] == '"':
                token = token[1:]
            if token[-1] == '"':
                token = token[:-1]
            current_phrase.append(token.lower())
        else:
            phrases.append(current_phrase)
            current_phrase = []
    phrases.append(current_phrase)

    for phrase in phrases:
        doc_lists = []
        if len(phrase) > 1:
            relevant_docs = get_doc_for_phrase(phrase)
        else:
            relevant_docs = process_freetext_query(phrase)[0]
            print(relevant_docs)
        doc_lists.append(relevant_docs)

    # Sort the docs contains relevant phrase with the one with fewest elements at the bottom
    doc_lists.sort(key=lambda x: len(x), reverse=True)

    # Merge the postings from the shortest to longest one
    while len(doc_lists) > 1:
        p1 = doc_lists.pop()
        p2 = doc_lists.pop()
        merged_posting = and_operation(p1,p2)
        doc_lists.append(merged_posting)

    return doc_lists[0]

def process_rocchio_freetext_query(query_vector):
    scores = {}
    for token in query_vector.keys():
        if token in dictionary.keys():
            posting = read_normal_posting_list(dictionary[token])
        else:
            posting = []
        for doc in posting:
            if doc[0] in scores:
                scores[doc[0]] += float(doc[1])*(query_vector[token])
            else:
                scores[doc[0]] = float(doc[1])*(query_vector[token])
    # chosen_docs = heapq.nlargest(K, scores.items(), key=lambda i: i[1])
    print("========scores for rocchio =======")
    print(scores)
    return list(map(lambda x: x[0], scores.items()))




def process_freetext_query(expression_tokens):
    scores = {}
    docVectors = {}
    N = len(doc_freq.keys())
    result = ''
    tokens = []
    for token in expression_tokens:
        tokens.append(process_token(token))
    # Get FreqDist of queries
    fd = get_freq_dist(tokens)
    tokens = fd.keys()
    query_model = {}

    query_length_square = 0

    # Construct query model
    for token in tokens:
        # l
        tf_wt = 1 + math.log(fd[token], 10)
        # t
        if token in doc_freq.keys():
            df = doc_freq[token]
        else:
            df = 0
        if df == 0:
            idf = 0
        else:
            idf = math.log(N / df, 10)
        # c (has not done the actual normalization yet, just accumulating data)
        w_tq = tf_wt * idf
        query_model[token] = w_tq
        query_length_square += w_tq**2

    query_length = math.sqrt(query_length_square)


    for token in tokens:
        if token in dictionary.keys():
            posting = read_normal_posting_list(dictionary[token])
        else:
            posting = []
        for doc in posting:
            if doc[0] in scores:
                scores[doc[0]] += float(doc[1])*(query_model[token]/query_length)
            else:
                scores[doc[0]] = float(doc[1])*(query_model[token]/query_length)
            if doc[0] in docVectors:
                docVectors[doc[0]][token] = float(doc[1])
            else:
                docVectors[doc[0]] = {}
                docVectors[doc[0]]= dict.fromkeys(query_model.keys(),0)
                docVectors[doc[0]][token] = float(doc[1])
    chosen_docs = heapq.nlargest(K, scores.items(), key=lambda i: i[1])
    print("========scores for normal=======")
    print(scores)
    return (list(map(lambda x: x[0], chosen_docs)), query_model, docVectors)


def rocchio (query_vector, doc_vectors):

    alpha = 1
    beta = 0.75

    updated_query = {}
    for doc in doc_vectors.keys():
        for term in doc_vectors[doc].keys():
            if term not in updated_query:
                updated_query[term] = beta * doc_vectors[doc][term] + query_vector[term]
            else:
                updated_query[term] += beta * doc_vectors[doc][term]
    return updated_query


def process_query(expression_tokens):
    """
    Process query and return an array of cases valid as result
    """
    if "AND" in expression_tokens:

        result = process_boolean_query(expression_tokens)

    elif expression_tokens[0][0] == '"':
        result = process_boolean_query(expression_tokens)
    else:
        expression_tokens = expand_query(expression_tokens)
        resultSet = process_freetext_query(expression_tokens)
        result = resultSet[0]
        # print(" print(resultSet[0])")
        # print(resultSet[0])
        # print(" print(resultSet[1])")
        # print(resultSet[1])
        # print(" print(resultSet[2])")
        # print(resultSet[2])
        updated_query = rocchio(resultSet[1],resultSet[2])
        result_rocchio = process_rocchio_freetext_query(updated_query)
        print("========result=======")
        print(result)
        print("========result rocchio=======")
        print(result_rocchio)

    #
    return result


def usage():
    print("usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results")


dictionary_file = postings_file = file_of_queries = output_file_of_results = None

try:
    opts, args = getopt.getopt(sys.argv[1:], 'd:p:q:o:')
except getopt.GetoptError:
    usage()
    sys.exit(2)

for o, a in opts:
    if o == '-d':
        dictionary_file = a
    elif o == '-p':
        postings_file = a
    elif o == '-q':
        file_of_queries = a
    elif o == '-o':
        file_of_output = a
    else:
        assert False, "unhandled option"

if dictionary_file == None or postings_file == None or file_of_queries == None or file_of_output == None:
    usage()
    sys.exit(2)

positional_dictionary = load_positional_dictionary(dictionary_file)
dictionary = load_dictionary(dictionary_file)
doc_freq = load_doc_freq()

# Get list of queries in the form of expression tokens list
query = load_query(file_of_queries)


write_output = ''
write_output += " ".join(process_query(query)).strip() + '\n'

fo = open(file_of_output, 'w')
fo.write(write_output)
fo.close()