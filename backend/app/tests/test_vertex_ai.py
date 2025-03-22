from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel


def test_vertex_ai_connection():
    """Test if Vertex AI is properly configured"""
    try:
        # Initialize Vertex AI
        aiplatform.init(project="memento-98a1c")

        # Try to load an embedding model
        model = TextEmbeddingModel.from_pretrained(
            "textembedding-gecko@latest")

        # Test a simple embedding
        embeddings = model.get_embeddings(["Hello, world!"])

        # If we got here, it's working
        print("✅ Vertex AI is properly configured!")
        print(
            f"Generated embedding with {len(embeddings[0].values)} dimensions")

        return True
    except Exception as e:
        print("❌ Vertex AI configuration failed:")
        print(f"Error: {e}")
        print("\nPossible solutions:")
        print("1. Check if your GCP_PROJECT_ID is correct")
        print("2. Verify that you've set up authentication credentials")
        print("3. Ensure Vertex AI API is enabled in your GCP project")
        print("4. Check your network connection to Google Cloud")

        return False


if __name__ == "__main__":
    test_vertex_ai_connection()
