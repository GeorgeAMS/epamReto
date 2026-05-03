from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams


def main() -> None:
    client = QdrantClient(url="http://localhost:6333")
    collections = {c.name for c in client.get_collections().collections}
    if "pokedex_strategy" not in collections:
        client.create_collection(
            collection_name="pokedex_strategy",
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
        print("created:pokedex_strategy")
    else:
        print("exists:pokedex_strategy")


if __name__ == "__main__":
    main()
