from semantic_search.upsert_pinecone import create_index

def main():
    index_name = "x-comments-markus-odenthal"
    create_index(index_name=index_name)

if __name__ == "__main__":
    main()