import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Simple semantic cache using sentence-transformers and FAISS
class SemanticCache:
    def __init__(self, index_file="cache.index", map_file="cache_map.json", threshold=0.2):
        self.index_file = index_file
        self.map_file = map_file
        self.threshold = threshold
        # Using a small, fast model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = 384
        
        self.cache_store = {}
        
        if os.path.exists(self.index_file) and os.path.exists(self.map_file):
            self.index = faiss.read_index(self.index_file)
            with open(self.map_file, 'r') as f:
                # json keys are strings, convert back to int
                self.cache_store = {int(k): v for k, v in json.load(f).items()}
        else:
            self.index = faiss.IndexFlatL2(self.dimension)
            
    def get(self, question):
        if self.index.ntotal == 0:
            return None
            
        embedding = self.model.encode([question]).astype('float32')
        distances, indices = self.index.search(embedding, 1)
        
        # distance in L2; lower is more similar
        if distances[0][0] < self.threshold:
            idx = indices[0][0]
            print(f"Cache HIT (distance: {distances[0][0]:.3f}) for question: {question}")
            return self.cache_store.get(idx)
            
        print(f"Cache MISS (closest distance: {distances[0][0]:.3f}) for question: {question}")
        return None
        
    def put(self, question, sql):
        embedding = self.model.encode([question]).astype('float32')
        pos = self.index.ntotal
        
        self.index.add(embedding)
        self.cache_store[pos] = sql
        
        # Save to disk
        faiss.write_index(self.index, self.index_file)
        with open(self.map_file, 'w') as f:
            json.dump(self.cache_store, f)
