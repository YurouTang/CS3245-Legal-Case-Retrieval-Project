import sys
import getopt
import pickle
import math
import string

from os import listdir
from os.path import isfile, join

from tokenize_word import *


# Set up positional dictionary and posting
positional_dictionary = {}
positional_posting = {}
# Set up non-positional dictionary and posting
dictionary = {}
posting = {}
# Document frequency dict
doc_freq = {}
# Court case dict

##------------------ Computations -------------------##
def get_lf(freq):
	"""
	Get log of frequency
	"""
	if freq == 0:
		return 0
	return 1 + math.log10(freq)


##------------------ I/O -------------------##
def write_positional_posting(output_pos, output_dic):
	"""
	Write positional dictionary and postings to files
	"""
	positions_file = open('positions.txt', 'w')
	pos_file = open('positional_' + output_pos, 'w')
	posting_byte_offset = {}

	for term in positional_posting:
		position_byte_offset = {}
		documents_with_term = positional_posting[term]

		posting_byte_offset[term] = pos_file.tell()
		for doc_id in documents_with_term:
			positions = documents_with_term[doc_id]

			position_byte_offset[doc_id] = positions_file.tell()
			for position in positions:
				positions_file.write(str(position) + " ")
			positions_file.write("\n")

			pos_file.write(str(doc_id) + " " + str(position_byte_offset[doc_id]) + " ")
		pos_file.write("\n")
	pos_file.close()
	
	for term in positional_dictionary:
		positional_dictionary[term] = [positional_dictionary[term], posting_byte_offset[term]]
	pickle.dump(positional_dictionary, open('positional_' + output_dic, 'wb'))


def write_normal_posting(output_pos, output_dic):
	"""
	Write non-positional posting and dictionary to file
	"""
	f = open(output_pos, 'w')
	position = f.tell()
	for term in posting.keys():
		dictionary[term] = position
		f.write(str(posting[term]))
		f.write('\n')
		position = f.tell()
	f.close()
	pickle.dump(dictionary, open(output_dic, 'wb'))


##------------------ Indexing -------------------##
def add_term_to_positional_posting(row):
	"""
	Indexing terms in postional posting
	"""
	document_id = row[0]
	title = row[1]
	content = row[2]
	date_posted = row[3]
	court = row[4]
	# Remove punctuation
	new_string = ""
	for character in content:
		if character not in list(string.punctuation):
		   new_string = new_string + character

	term_list = new_string.split()

	position = 1
	for term in term_list:
		# Case-folding
		term = term.lower()

		if term not in positional_dictionary:
			positional_dictionary[term] = 1
			positional_posting[term] = {document_id : [position]}
		elif document_id not in positional_posting[term]:
			positional_dictionary[term] += 1
			positional_posting[term][document_id] = []
		positional_posting[term][document_id].append(position)
		position += 1


def add_term_to_normal_posting(row):
	"""
	Indexing terms in non-positional posting
	"""	
	document_id = row[0]

	tokens = []
	for content in row:
		tks = get_tokens(content)
		tokens.extend(tks)
	df = get_freq_dist(tokens)
	doc_length_square = 0
	unique_tokens = df.keys()
	temp = {}

	for token in unique_tokens:
		freq = df[token]
		doc_length_square += get_lf(freq)**2
		temp[token] = freq
		if token in doc_freq:
			doc_freq[token] += 1
		else:
			doc_freq[token] = 1

	doc_length = math.sqrt(doc_length_square)

	for token in unique_tokens:
		n_w = round(get_lf(freq)/doc_length, 6) #naturalized wt
		if token in posting:
			posting[token].append((document_id, n_w))	
		else:
			posting[token] = [(document_id, n_w)]


def index_documents(input_dir, output_file_dic, output_file_pos):
	"""
	To index all documents in reuters.
	positional_dictionary contains all token with its respectively doc frequency and offset.
	Postings stores the token's respective positional_posting list.
	"""
	print('indexing documents...')

	import csv
	# csv.field_size_limit(sys.maxsize)
	maxInt = sys.maxsize

	while True:
		# decrease the maxInt value by factor 10
		# as long as the OverflowError occurs.
		try:
			csv.field_size_limit(maxInt)
			break
		except OverflowError:
			maxInt = int(maxInt / 10)

	row_count = 0
	
	with open(input_dir, encoding="utf8") as csv_file:
		csv_reader = csv.reader(csv_file, delimiter=',', quotechar='"')
		for row in csv_reader:
			if row_count == 0:
				print("Column names are %s" % (", ".join(row)))
			else:
				add_term_to_positional_posting(row)
				add_term_to_normal_posting(row)
				print("Indexing document number %d, case id %s" %(row_count, row[0]))
			row_count += 1	
		write_positional_posting(output_file_pos, output_file_dic)
		write_normal_posting(output_file_pos, output_file_dic)
		pickle.dump(doc_freq, open('doc_freq', 'wb'))


def usage():
	print("usage: " + sys.argv[0] + " -i directory-of-documents -d positional_dictionary-file -p postings-file")


input_directory = output_file_dictionary = output_file_postings = None

try:
	opts, args = getopt.getopt(sys.argv[1:], 'i:d:p:')
except getopt.GetoptError:
	usage()
	sys.exit(2)

for o, a in opts:
	if o == '-i':  # input directory
		input_directory = a
	elif o == '-d':  # positional_dictionary file
		output_file_dictionary = a
	elif o == '-p':  # postings file
		output_file_postings = a
	else:
		assert False, "unhandled option"

if input_directory == None or output_file_postings == None or output_file_dictionary == None:
	usage()
	sys.exit(2)

index_documents(input_directory, output_file_dictionary, output_file_postings);
