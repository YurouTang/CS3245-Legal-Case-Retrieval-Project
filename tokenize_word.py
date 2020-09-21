from nltk.tokenize import word_tokenize
from nltk.stem.porter import *
from nltk import FreqDist
from nltk.corpus import stopwords

def read_text(path):
	"""
	Read entire text body from 1 training file
	"""
	f = open(path)
	raw = f.read()
	return raw

def get_tokens(raw):
	"""
	Tokenize words from text
	"""
	unprocessed_tokens = word_tokenize(raw)
	tokens = [process_token(token) for token in unprocessed_tokens]

	return tokens

def get_freq_dist(tokens):
	"""
	Get fd of documents
	"""
	freq_dist = FreqDist(tokens)
	return freq_dist

def process_token(token):
	"""
	Lowercase and stem token
	"""
	stemmer =  PorterStemmer()
	t = token.lower()
	t = stemmer.stem(t)
	return t


def remove_Stopwords(line):
    stop_words = set(stopwords.words("english"))
    filtered_words = [w for w in line if not w in stop_words]
    return filtered_words