import json

import chromadb
from tqdm import tqdm as tqdm_func
import torch
from chromadb.utils import embedding_functions
from icecream import ic

class ChromaDB:
    #TODO only Delete removed entries (missing id) and then upsert database, because it's a heavy process
    settings = json.load(open("./settings/settings.json"))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="intfloat/multilingual-e5-large",
        cache_folder=settings["model_cache_directory"],
        device=device,
    )
    client = chromadb.PersistentClient(path=settings["chromadb_path"])

    @classmethod
    def replace_data(cls, collection, documents, ids, metadata=None):
        try:
            cls.client.delete_collection(name=collection)
        except Exception as e:
            ic()
            ic(f"Collection didn't exist or couldn't be deleted: {str(e)}")

        collection = cls.client.create_collection(
            name=collection,
            embedding_function=cls.embedding_function
        )

        try:
            batch_size = 100
            total_docs = len(documents)

            if total_docs > batch_size:
                for i in tqdm_func(range(0, total_docs, batch_size), desc=f"Adding documents to {collection.name}"):
                    end_idx = min(i + batch_size, total_docs)
                    batch_docs = documents[i:end_idx]
                    batch_ids = ids[i:end_idx]

                    batch_meta = None
                    if metadata is not None:
                        batch_meta = metadata[i:end_idx]

                    collection.add(
                        documents=batch_docs,
                        metadatas=batch_meta,
                        ids=batch_ids
                    )
            else:
                with tqdm_func(total=1, desc=f"Adding documents to {collection.name}") as pbar:
                    collection.add(documents=documents, metadatas=metadata, ids=ids)
                    pbar.update(1)

            return True
        except Exception as e:
            ic()
            ic(f"Error adding documents to collection {collection.name}: {str(e)}")
            return False

    @classmethod
    def retrieve(cls, collection, query, n_results=5, filter_condition=None):
        #TODO should query all collections by default
        try:
            collection = cls.client.get_collection(
                name=collection,
                embedding_function=cls.embedding_function
            )

            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter_condition
            )

            return results
        except Exception as e:
            ic()
            ic(f"Error retrieving data from collection {collection}: {str(e)}")
            return collection
