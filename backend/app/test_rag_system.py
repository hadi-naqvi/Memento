# test_rag_system.py

import os
import json
import base64
import tempfile
from datetime import datetime
from google_rag_system import MementoRAGSystem

# Import Google Cloud services
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
from dotenv import load_dotenv

from firebase_init import db as firebase_db

from google_rag_system import MementoRAGSystem

load_dotenv()


def load_sample_ids():
    """Load sample IDs from the generated JSON file"""
    try:
        with open("sample_ids.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading sample_ids.json: {e}")
        return None


def test_text_processing():
    """Test the RAG system with a text message"""
    print("\n=== Testing Text Processing ===")

    # Initialize the RAG system
    rag = MementoRAGSystem()

    # Load sample patient IDs
    samples = load_sample_ids()
    if not samples or not samples.get("patients"):
        print("No sample patients available. Please check sample_ids.json")
        return

    # Get the first patient ID
    patient_id = samples["patients"][0]
    print(f"Using patient ID: {patient_id}")

    # Test message
    test_message = "Can you tell me about my family?"
    print(f"Test message: '{test_message}'")

    # Process the message
    print("Processing message...")
    result = rag.process_text_message(patient_id, test_message)

    # Display results
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print("\nRetrieved Memories:")
        for i, memory in enumerate(result.get("memories", [])):
            print(
                f"  {i+1}. {memory['summary']} (Similarity: {memory['similarity']:.2f})"
            )

        print(f"\nSentiment: {result.get('sentiment', 'unknown')}")
        print(f"\nAI Response: {result.get('response', '')}")

        # Check if audio response is available
        if "audioResponse" in result:
            audio_file = f"test_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            with open(audio_file, "wb") as f:
                f.write(base64.b64decode(result["audioResponse"]))
            print(f"\nAudio response saved to: {audio_file}")


def test_audio_processing():
    """Test the RAG system with an audio file"""
    print("\n=== Testing Audio Processing ===")

    # Check if we have a test audio file
    test_audio_file = "test_audio.wav"
    if not os.path.exists(test_audio_file):
        print(f"Test audio file not found: {test_audio_file}")
        print(
            "Please create a test audio file using the 'Upload test audio file' option."
        )
        return

    # Initialize the RAG system
    rag = MementoRAGSystem()

    # Load sample patient IDs
    samples = load_sample_ids()
    if not samples or not samples.get("patients"):
        print("No sample patients available. Please check sample_ids.json")
        return

    # Get the first patient ID
    patient_id = samples["patients"][0]
    print(f"Using patient ID: {patient_id}")

    # Read the audio file
    with open(test_audio_file, "rb") as f:
        audio_content = f.read()

    print(f"Using audio file: {test_audio_file}")

    # Process the audio
    print("Processing audio...")
    result = rag.process_audio_message(patient_id, audio_content)

    # Display results
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"\nTranscribed message: '{result.get('message', '')}'")

        print("\nRetrieved Memories:")
        for i, memory in enumerate(result.get("memories", [])):
            print(
                f"  {i+1}. {memory['summary']} (Similarity: {memory['similarity']:.2f})"
            )

        print(f"\nSentiment: {result.get('sentiment', 'unknown')}")
        print(f"\nAI Response: {result.get('response', '')}")

        # Check if audio response is available
        if "audioResponse" in result:
            audio_file = f"test_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            with open(audio_file, "wb") as f:
                f.write(base64.b64decode(result["audioResponse"]))
            print(f"\nAudio response saved to: {audio_file}")


def test_memory_retrieval():
    """Test memory retrieval directly"""
    print("\n=== Testing Memory Retrieval ===")

    # Initialize the RAG system
    rag = MementoRAGSystem()

    # Load sample patient IDs
    samples = load_sample_ids()
    if not samples or not samples.get("patients"):
        print("No sample patients available. Please check sample_ids.json")
        return

    # Get the first patient ID
    patient_id = samples["patients"][0]
    print(f"Using patient ID: {patient_id}")

    # Test queries
    test_queries = [
        "Tell me about my family", "What medication do I take?",
        "Where did I grow up?", "What did we talk about yesterday?"
    ]

    # Test each query
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        memories = rag.retrieve_memories(patient_id, query, limit=3)

        print("Retrieved Memories:")
        for i, memory in enumerate(memories):
            print(
                f"  {i+1}. {memory.get('summary', '')} (Similarity: {memory.get('similarity', 0.0):.2f})"
            )


def test_speech_processing():
    """Test speech-to-text and text-to-speech directly using Google Cloud"""
    print("\n=== Testing Speech Processing ===")

    # Initialize the RAG system
    rag = MementoRAGSystem()

    # Test text-to-speech
    print("Testing text-to-speech...")
    test_text = "Hello, this is a test of the speech synthesis capability of the Memento system."
    try:
        audio_content = rag.text_to_speech(test_text)
        audio_file = f"tts_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        with open(audio_file, "wb") as f:
            f.write(audio_content)
        print(f"Audio saved to: {audio_file}")
    except Exception as e:
        print(f"Error in text-to-speech: {e}")

    # Test speech-to-text if test audio file is available
    test_audio_file = "test_audio.wav"
    if os.path.exists(test_audio_file):
        print("\nTesting speech-to-text...")
        try:
            with open(test_audio_file, "rb") as f:
                audio_content = f.read()

            transcript = rag.speech_to_text(audio_content)
            print(f"Transcription: '{transcript}'")
        except Exception as e:
            print(f"Error in speech-to-text: {e}")
    else:
        print(
            f"\nSkipping speech-to-text test. Test audio file not found: {test_audio_file}"
        )
        print("Upload a test audio file to test this functionality.")


def test_sentiment_analysis():
    """Test sentiment analysis and entity extraction"""
    print("\n=== Testing Sentiment Analysis ===")

    # Initialize the RAG system
    rag = MementoRAGSystem()

    # Test messages with different sentiments
    test_messages = [
        "I'm feeling happy today and I enjoyed talking to my grandson Michael.",
        "I'm confused about my medication schedule and I feel worried.",
        "I remember growing up in Chicago with my sister Jane. Those were good times.",
        "The doctor said my condition is stable but I need to continue my treatment."
    ]

    for message in test_messages:
        print(f"\nAnalyzing: '{message}'")
        try:
            sentiment_data = rag.analyze_sentiment(message)

            print(f"Sentiment: {sentiment_data.get('category', 'unknown')}")
            print(f"Score: {sentiment_data.get('score', 0):.2f}")
            print(f"Magnitude: {sentiment_data.get('magnitude', 0):.2f}")

            print("Entities:")
            for entity_type, entities in sentiment_data.get('entities',
                                                            {}).items():
                if entities:
                    print(f"  {entity_type}: {', '.join(entities)}")
        except Exception as e:
            print(f"Error in sentiment analysis: {e}")


def upload_audio_to_cloud(local_file_path, bucket_name=None):
    """Upload audio file to Google Cloud Storage for processing"""
    try:
        # Check if bucket name is provided, otherwise use default
        if not bucket_name:
            bucket_name = os.environ.get("GCP_AUDIO_BUCKET",
                                         "memento-test-audio")

        # Create a unique blob name
        blob_name = f"test_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"

        # Initialize client
        storage_client = storage.Client()

        # Check if bucket exists, create if it doesn't
        try:
            bucket = storage_client.get_bucket(bucket_name)
        except Exception:
            print(f"Bucket {bucket_name} does not exist. Creating...")
            bucket = storage_client.create_bucket(bucket_name)

        # Upload file
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_file_path)

        gcs_uri = f"gs://{bucket_name}/{blob_name}"
        print(f"File uploaded to: {gcs_uri}")

        return gcs_uri
    except Exception as e:
        print(f"Error uploading to Cloud Storage: {e}")
        return None


def transcribe_gcs_audio(gcs_uri):
    """Transcribe audio file from Google Cloud Storage"""
    try:
        client = speech.SpeechClient()

        audio = speech.RecognitionAudio(uri=gcs_uri)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            enable_automatic_punctuation=True,
            model="latest_long")

        operation = client.long_running_recognize(config=config, audio=audio)
        print("Waiting for operation to complete...")
        response = operation.result(timeout=90)

        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript

        return transcript
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None


def upload_test_audio():
    """Upload an existing audio file for testing"""
    print("\n=== Upload Test Audio File ===")

    # Ask for file path
    file_path = input(
        "Enter the path to your audio file (WAV format preferred): ")

    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    # Option 1: Copy the file locally
    local_option = input(
        "Do you want to copy this file locally as test_audio.wav? (y/n): ")
    if local_option.lower() == 'y':
        import shutil
        try:
            shutil.copy(file_path, "test_audio.wav")
            print("File copied to test_audio.wav")
        except Exception as e:
            print(f"Error copying file: {e}")

    # Option 2: Upload to Google Cloud Storage
    cloud_option = input(
        "Do you want to upload this file to Google Cloud Storage? (y/n): ")
    if cloud_option.lower() == 'y':
        gcs_uri = upload_audio_to_cloud(file_path)
        if gcs_uri:
            # Offer to transcribe
            transcribe_option = input(
                "Do you want to transcribe this audio file? (y/n): ")
            if transcribe_option.lower() == 'y':
                transcript = transcribe_gcs_audio(gcs_uri)
                if transcript:
                    print(f"Transcription: '{transcript}'")


def use_cloud_speech_recognition():
    """Use Google Cloud Speech-to-Text API for live audio"""
    print("\n=== Live Audio Transcription ===")
    print(
        "This feature requires using the Web/Mobile application with the API.")
    print("For testing purposes, please upload an audio file instead.")

    # Provide guidance
    print("\nTo test with live audio:")
    print("1. Use the Memento mobile/web app to record audio")
    print("2. The app will send the audio to the API")
    print(
        "3. Alternatively, you can use Google Cloud Console's Speech-to-Text demo"
    )
    print("   https://cloud.google.com/speech-to-text")


def interactive_chat():
    """Interactive chat session for testing"""
    print("\n=== Interactive Chat Session ===")

    project_id = os.getenv("GCP_PROJECT_ID", "test-project-id")
    rag = MementoRAGSystem(project_id=project_id, db=firebase_db)

    # Load sample patient IDs
    samples = load_sample_ids()
    if not samples or not samples.get("patients"):
        print("No sample patients available. Please check sample_ids.json")
        return

    # Show available patients
    print("\nAvailable patients:")
    for i, patient_id in enumerate(samples.get("patients", [])):
        try:
            from firebase_admin import firestore
            db = firestore.client()
            patient_doc = db.collection("users").document(patient_id).get()
            if patient_doc.exists:
                patient = patient_doc.to_dict()
                print(
                    f"{i+1}. {patient.get('displayName')} (ID: {patient_id})")
        except Exception as e:
            print(f"Error loading patient {patient_id}: {e}")

    # Select a patient
    selection = input(
        "\nSelect a patient number (or press Enter for first patient): ")
    try:
        if selection.strip():
            index = int(selection) - 1
            patient_id = samples.get("patients")[index]
        else:
            patient_id = samples.get("patients")[0]

        from firebase_admin import firestore
        db = firestore.client()
        patient_doc = db.collection("users").document(patient_id).get()
        patient = patient_doc.to_dict()
        print(f"\nChatting with {patient.get('displayName')}")
    except Exception as e:
        print(f"Error selecting patient: {e}")
        print("Using the first patient.")
        patient_id = samples.get("patients")[0]

    # Start chat session
    print("\n=== Chat Session Started ===")
    print("Type 'exit' to end the conversation")
    print("Type 'memories' to view memories for your last query")
    print("Type 'audio:file.wav' to send an audio file")

    last_memories = []

    while True:
        # Get user input
        user_input = input("\nYou: ")
        if user_input.lower() == "exit":
            break

        if user_input.lower() == "memories":
            print("\nRelevant memories for your last query:")
            for i, memory in enumerate(last_memories):
                print(
                    f"  {i+1}. {memory.get('summary', '')} (Similarity: {memory.get('similarity', 0.0):.2f})"
                )
            continue

        # Check if user wants to send an audio file
        if user_input.startswith("audio:"):
            audio_file_path = user_input[6:].strip()
            if not os.path.exists(audio_file_path):
                print(f"Error: Audio file not found at {audio_file_path}")
                continue

            print(f"Processing audio file: {audio_file_path}")
            with open(audio_file_path, "rb") as f:
                audio_content = f.read()

            print("Processing...")
            result = rag.process_audio_message(patient_id, audio_content)

            if "error" in result:
                print(f"Error: {result['error']}")
                continue

            print(f"You (transcribed): {result.get('message', '')}")

        else:
            # Process the text message
            print("Processing...")
            result = rag.process_text_message(patient_id, user_input)

        # Display results
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            # Store memories for later viewing
            last_memories = result.get("memories", [])

            # Print the response
            print(f"\nMia: {result.get('response', '')}")

            # Play and save audio response
            if "audioResponse" in result:
                audio_file = f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                with open(audio_file, "wb") as f:
                    f.write(base64.b64decode(result["audioResponse"]))
                print(f"(Audio response saved to: {audio_file})")

                # Try to play the audio (platform-dependent)
                try:
                    import platform
                    system = platform.system()

                    if system == "Windows":
                        os.system(f"start {audio_file}")
                    elif system == "Darwin":  # macOS
                        os.system(f"afplay {audio_file}")
                    else:  # Linux
                        os.system(f"xdg-open {audio_file}")
                except:
                    print("Could not automatically play the audio.")

    print("\n=== Chat Session Ended ===")


if __name__ == "__main__":
    print("Memento RAG System Test")
    print("=======================")
    print("1. Test text processing")
    print("2. Test audio processing")
    print("3. Test memory retrieval")
    print("4. Test speech processing (TTS/STT)")
    print("5. Test sentiment analysis")
    print("6. Upload test audio file")
    print("7. Cloud speech recognition info")
    print("8. Start interactive chat")

    choice = input("\nEnter your choice (1-8): ")

    if choice == "1":
        test_text_processing()
    elif choice == "2":
        test_audio_processing()
    elif choice == "3":
        test_memory_retrieval()
    elif choice == "4":
        test_speech_processing()
    elif choice == "5":
        test_sentiment_analysis()
    elif choice == "6":
        upload_test_audio()
    elif choice == "7":
        use_cloud_speech_recognition()
    elif choice == "8":
        interactive_chat()
    else:
        print("Invalid choice")
