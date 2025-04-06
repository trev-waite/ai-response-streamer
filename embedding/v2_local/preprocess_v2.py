from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle
import os

def read_chunks(file_path, max_words=500):
    """
    Generator function to yield text chunks of approximately max_words.
    
    Args:
        file_path (str): Path to the input text file.
        max_words (int): Target word count per chunk (default: 200).
    
    Yields:
        str: A chunk of text with approximately max_words.
    """
    current_chunk = []
    current_word_count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            words = line.split()
            if current_word_count + len(words) <= max_words:
                current_chunk.append(line.strip())
                current_word_count += len(words)
            else:
                yield " ".join(current_chunk)
                current_chunk = [line.strip()]
                current_word_count = len(words)
        if current_chunk:
            yield " ".join(current_chunk)

def main():
    # Configuration
    file_path = 'race-data/race_data_Bahrain_2024_Race-large.txt'
    model_name = 'all-MiniLM-L6-v2'  # Fast and efficient embedding model
    batch_size = 1000  # Number of chunks to embed in one batch

    print("Loading sentence-transformers model...")
    model = SentenceTransformer(model_name)

    # Process the file into chunks and generate embeddings
    print("Processing file and generating embeddings...")
    all_chunks = []
    embeddings = []
    for chunk in read_chunks(file_path):
        all_chunks.append(chunk)
        # Embed in batches to manage memory
        if len(all_chunks) % batch_size == 0:
            batch = all_chunks[-batch_size:]
            batch_embeddings = model.encode(batch, show_progress_bar=True)
            embeddings.extend(batch_embeddings)
    if len(all_chunks) % batch_size != 0:
        batch = all_chunks[-(len(all_chunks) % batch_size):]
        batch_embeddings = model.encode(batch, show_progress_bar=True)
        embeddings.extend(batch_embeddings)

    # Convert embeddings to a numpy array for FAISS
    embeddings = np.array(embeddings).astype('float32')
    print(f"Generated {len(embeddings)} embeddings.")

    # Create a FAISS index with ID mapping
    dimension = embeddings.shape[1]  # Embedding dimension (e.g., 384 for all-MiniLM-L6-v2)
    index = faiss.IndexIDMap(faiss.IndexFlatL2(dimension))  # Exact L2 distance search
    ids = np.arange(len(embeddings))  # Assign sequential IDs
    index.add_with_ids(embeddings, ids)
    print(f"Created FAISS index with {index.ntotal} vectors.")

    # Save the FAISS index and chunks to disk
    faiss.write_index(index, 'faiss_index.bin')
    with open('chunks.pkl', 'wb') as f:
        pickle.dump(all_chunks, f)
    print("Saved FAISS index to 'faiss_index.bin' and chunks to 'chunks.pkl'.")

    print("Preprocessing complete.")

if __name__ == "__main__":
    main()