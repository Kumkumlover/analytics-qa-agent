import os
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Semantic cache using TF-IDF + Cosine Similarity
# Runs 100% locally — zero API calls, zero model downloads.
class SemanticCache:
    def __init__(self, map_file="cache_map.json", threshold=0.6):
        self.map_file = map_file
        self.threshold = threshold  # cosine similarity; higher = more similar (0 to 1)
        
        self.questions = []   # list of cached question strings
        self.sql_map = {}     # index -> sql string
        
        if os.path.exists(self.map_file):
            with open(self.map_file, 'r') as f:
                data = json.load(f)
                self.questions = data.get('questions', [])
                self.sql_map = {int(k): v for k, v in data.get('sql_map', {}).items()}
            
    def get(self, question):
        if len(self.questions) == 0:
            return None
        
        # Build TF-IDF matrix over all cached questions + the new question
        corpus = self.questions + [question]
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(corpus)
        
        # Compare the new question (last row) against all cached questions
        similarities = cosine_similarity(tfidf_matrix[-1:], tfidf_matrix[:-1])[0]
        best_idx = int(np.argmax(similarities))
        best_score = similarities[best_idx]
        
        if best_score >= self.threshold:
            print(f"Cache HIT (similarity: {best_score:.3f}) for question: {question}")
            return self.sql_map.get(best_idx)
            
        print(f"Cache MISS (best similarity: {best_score:.3f}) for question: {question}")
        return None
        
    def put(self, question, sql):
        idx = len(self.questions)
        self.questions.append(question)
        self.sql_map[idx] = sql
        
        # Save to disk
        with open(self.map_file, 'w') as f:
            json.dump({
                'questions': self.questions,
                'sql_map': {str(k): v for k, v in self.sql_map.items()}
            }, f)
