import faiss
import numpy as np
import pickle
from google import genai
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Load the large file
with open('race-data/race_data_Bahrain_2024_Race-large.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Split into chunks (e.g., by paragraphs) MAY NEED TO UPDATE CHUNCK SPLITTING
chunks = [chunk.strip() for chunk in text.split('\n\n') if chunk.strip()]

embeddings = []
for chunk in chunks:
    embedding = client.models.embed_content(model='text-embedding-004', contents=chunk)
    embeddings.append(embedding.embeddings)

# Convert to numpy array
embeddings = np.array(embeddings).astype('float32')

# Create FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

# Save the index and chunks
faiss.write_index(index, 'racing_data.index')
with open('chunks.pkl', 'wb') as f:
    pickle.dump(chunks, f)

print("Preprocessing complete. FAISS index and chunks saved.")