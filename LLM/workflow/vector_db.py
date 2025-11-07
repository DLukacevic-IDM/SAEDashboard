from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from contextvars import ContextVar

from common import PDF_LOADER_PATH, CHROMA_DB_PATH

_EMBEDDING_MODEL = None


def get_embedding_model():
    global _EMBEDDING_MODEL
    _EMBEDDING_MODEL = _EMBEDDING_MODEL or HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            encode_kwargs={"normalize_embeddings": True}
        )
    return _EMBEDDING_MODEL


# Context variable to store tool outputs for workflow access
tool_outputs_context: ContextVar[dict] = ContextVar('tool_outputs', default={})


def setup_vector_db():
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    import os
    import json

    from common import CHROMA_DB_PATH

    pdf_files = [os.path.join(PDF_LOADER_PATH, f) for f in os.listdir(PDF_LOADER_PATH) if f.endswith('.pdf')]

    docs = []
    for pdf_file in pdf_files:
        loader = PyPDFLoader(pdf_file)
        docs.extend(loader.load())

    for i, doc in enumerate(docs):
        print(f"Document {i + 1} length: {doc.page_content}")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_docs = text_splitter.split_documents(docs)

    # Add chunk id to metadata
    for i, doc in enumerate(split_docs):
        doc.metadata['chunk_id'] = i + 1  # Start chunk_id from 1

    print(f"Number of text chunks: {len(split_docs)}")

    # print char count for each chunk
    for i, doc in enumerate(split_docs):
        print(f"Chunk {i + 1} length: {len(doc.page_content)} characters")

    # print metadata for the 2nd chunk as an example
    print(json.dumps(split_docs[1].metadata, indent=4))

    # Create vector store
    Path(CHROMA_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    chroma_db = Chroma.from_documents(
        documents=split_docs,
        embedding=get_embedding_model(),
        persist_directory=CHROMA_DB_PATH
    )

    print("Done.")
    return chroma_db


def ask_vector_db(query: str) -> str:
    """Ask a question using RAG and ChromaDB similarity search.

    Args:
        query (str): The question to search for.

    Returns:
        str: A formatted string with the raw search results for the agent to use.
    """
    # Initialize embeddings and load ChromaDB
    chroma_db = Chroma(
        persist_directory=CHROMA_DB_PATH,
        embedding_function=get_embedding_model()
    )

    # Perform direct similarity search (returns k most similar documents)
    search_results = chroma_db.similarity_search(query, k=4)

    # Extract references from search results with full metadata
    references = []
    for doc in search_results:
        references.append({
            'source': doc.metadata.get('source', 'Unknown'),
            'title': doc.metadata.get('title', 'Unknown Title'),
            'page_label': doc.metadata.get('page_label', 'Unknown'),
            'chunk_id': str(doc.metadata.get('chunk_id', 'Unknown')),
            'page_content_preview': doc.page_content[:200]
        })

    # Format results as a string for the agent to use
    if not search_results:
        result_text = "No relevant information found in the knowledge base."
    else:
        result_text = "Found the following relevant information:\n\n"
        for i, doc in enumerate(search_results, 1):
            result_text += f"[Source {i}]\n"
            result_text += f"Content: {doc.page_content}\n"
            result_text += f"Source: {doc.metadata.get('source', 'Unknown')}\n"
            result_text += f"Page: {doc.metadata.get('page_label', 'Unknown')}\n\n"

    # Store structured data in context for workflow to access
    context_data = tool_outputs_context.get()
    context_data['ask_vector_db'] = {
        'answer': result_text,
        'references': references,
        'num_sources': len(references),
        'called': True,
        'search_results': search_results  # Store raw Document objects
    }
    tool_outputs_context.set(context_data)

    # Return formatted text for the agent to use
    return result_text


def main():
    if Path(CHROMA_DB_PATH).is_file():
        print(f"ChromaDB found at {CHROMA_DB_PATH}. Skipping setup.")
        return
    else:
        print(f"Creating ChromaDB vector database and embeddings content.")
        
    import time

    start_time = time.perf_counter()

    # Setup vector database (uncomment if running for the first time or adding new PDFs)
    setup_vector_db()

    # Example query
    query = "Quelles sont les six régions qui représentent 90 % des cas de paludisme au Sénégal?"

    # Ask RAG
    answer = ask_vector_db(query)
    print("RAG Answer:\n", answer)

    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time:.4f} seconds")
    

if __name__ =="__main__":
    main()
