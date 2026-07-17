from app.services.ollama_service import OllamaService


def main() -> None:
    client = OllamaService(embed_model="nomic-embed-text")
    text = "FastAPI permite construir APIs modernas y rapidas en Python."
    embedding = client.generate_embedding(text)

    print(f"Dimension del embedding: {len(embedding)}")
    print(f"Primeros 5 valores: {embedding[:5]}")


if __name__ == "__main__":
    main()
