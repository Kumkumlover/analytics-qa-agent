import os
import json
import faiss
import numpy as np
import google.generativeai as genai

# Semantic cache using Google Gemini Embeddings + FAISS
# This avoids downloading the 80MB sentence-transformers model which hangs on Streamlit Cloud.
class SemanticCache:
    def __init__(self, index_file="cache.index", map_file="cache_map.json", threshold=0.25):
        self.index_file = index_file
        self.map_file = map_file
        self.threshold = threshold
        self.dimension = 768  # text-embedding-004 output dimension

        # Configure Gemini
        api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get('GEMINI_API_KEY') or st.secrets.get('GOOGLE_API_KEY')
            except Exception:
                pass
        if api_key:
            genai.configure(api_key=api_key)
        
        self.cache_store = {}
        
        if os.path.exists(self.index_file) and os.path.exists(self.map_file):
            self.index = faiss.read_index(self.index_file)
            with open(self.map_file, 'r') as f:
                # json keys are strings, convert back to int
                self.cache_store = {int(k): v for k, v in json.load(f).items()}
        else:
            self.index = faiss.IndexFlatL2(self.dimension)

    def _embed(self, text):
        """Get embedding from Google's text-embedding-004 model."""
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text
        )
        return np.array([result['embedding']], dtype='float32')
            
    def get(self, question):
        if self.index.ntotal == 0:
            return None
            
        embedding = self._embed(question)
        distances, indices = self.index.search(embedding, 1)
        
        # distance in L2; lower is more similar
        if distances[0][0] < self.threshold:
            idx = indices[0][0]
            print(f"Cache HIT (distance: {distances[0][0]:.3f}) for question: {question}")
            return self.cache_store.get(idx)
            
        print(f"Cache MISS (closest distance: {distances[0][0]:.3f}) for question: {question}")
        return None
        
    def put(self, question, sql):
        embedding = self._embed(question)
        pos = self.index.ntotal
        
        self.index.add(embedding)
        self.cache_store[pos] = sql
        
        # Save to disk
        faiss.write_index(self.index, self.index_file)
        with open(self.map_file, 'w') as f:
            json.dump(self.cache_store, f)
