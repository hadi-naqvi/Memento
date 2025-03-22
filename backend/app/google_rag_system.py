# google_rag_system.py

import os
import base64
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Google Cloud imports
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
from google.cloud import aiplatform
from google.cloud import language_v1
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel
from firebase_admin import firestore


class MementoRAGSystem:
    """Retrieval-Augmented Generation system for Memento using Google Cloud services"""

    def __init__(self, project_id=None, db=None):
        """Initialize the RAG system with Google Cloud clients"""
        # Get project ID from environment variable if not provided
        self.project_id = project_id or os.environ.get("GCP_PROJECT_ID")
        if not self.project_id:
            print("Warning: GCP_PROJECT_ID not set. Using 'test-project-id'")
            self.project_id = "test-project-id"

        try:
            # Initialize Vertex AI
            aiplatform.init(project=self.project_id)

            # Initialize clients
            self.speech_client = speech.SpeechClient()
            self.tts_client = texttospeech.TextToSpeechClient()
            self.language_client = language_v1.LanguageServiceClient()

            # Initialize models
            self.embedding_model = TextEmbeddingModel.from_pretrained(
                "textembedding-gecko@latest")
            self.gemini_model = GenerativeModel("gemini-pro")

            # Get Firestore client - use the provided one or import from firebase_init
            if db is not None:
                self.db = db
            else:
                # Import the already initialized Firebase
                from firebase_init import db as firebase_db
                self.db = firebase_db

            print(
                f"Memento RAG System initialized with project ID: {self.project_id}"
            )
        except Exception as e:
            print(f"Error initializing RAG system: {e}")
            raise

    def text_to_speech(self, text: str, language_code: str = "en-US") -> bytes:
        """Convert text to speech using Google Cloud Text-to-Speech"""
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Configure voice
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name="en-US-Neural2-C",
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE)

        # Configure audio
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.9,  # Slightly slower for Alzheimer's patients
            pitch=0.0,
            volume_gain_db=1.0)

        response = self.tts_client.synthesize_speech(input=synthesis_input,
                                                     voice=voice,
                                                     audio_config=audio_config)

        return response.audio_content

    def generate_embedding(self, text: str) -> List[float]:
        """Generate text embeddings using Vertex AI"""
        embeddings = self.embedding_model.get_embeddings([text])
        return embeddings[0].values

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment and extract entities using Natural Language API"""
        document = language_v1.Document(
            content=text, type_=language_v1.Document.Type.PLAIN_TEXT)

        # Analyze sentiment
        sentiment = self.language_client.analyze_sentiment(request={
            "document": document
        }).document_sentiment

        # Analyze entities
        entities_response = self.language_client.analyze_entities(
            request={"document": document})

        # Organize entities by type
        extracted_entities = {
            "people": [],
            "locations": [],
            "organizations": [],
            "other": []
        }

        for entity in entities_response.entities:
            entity_type = language_v1.Entity.Type(entity.type_).name
            if entity_type == "PERSON":
                extracted_entities["people"].append(entity.name)
            elif entity_type in ["LOCATION", "ADDRESS"]:
                extracted_entities["locations"].append(entity.name)
            elif entity_type == "ORGANIZATION":
                extracted_entities["organizations"].append(entity.name)
            else:
                extracted_entities["other"].append(entity.name)

        # Determine sentiment category
        sentiment_score = sentiment.score
        sentiment_category = "neutral"
        if sentiment_score > 0.25:
            sentiment_category = "positive"
        elif sentiment_score < -0.25:
            sentiment_category = "negative"
        elif len(extracted_entities["people"]) > 0:
            sentiment_category = "family"  # Special category for family mentions

        return {
            "score": sentiment_score,
            "magnitude": sentiment.magnitude,
            "category": sentiment_category,
            "entities": extracted_entities
        }

    def retrieve_memories(self,
                          patient_id: str,
                          query_text: str,
                          limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant memories for a patient based on query text"""
        # Generate query embedding
        query_embedding = self.generate_embedding(query_text)

        try:
            # Try using Firestore's vector search with the newer API
            from google.cloud.firestore_v1.vector import Vector
            from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

            # Get the chunks collection reference
            chunks_ref = self.db.collection("patientMemoryVectors").document(
                patient_id).collection("chunks")

            # Perform vector search
            vector_query = chunks_ref.find_nearest(
                vector_field="vector",
                query_vector=Vector(query_embedding),
                distance_measure=DistanceMeasure.COSINE,
                limit=limit)

            # Get the results
            results = vector_query.stream()

            memories = []
            for doc in results:
                memory = doc.to_dict()
                # Add the similarity score (1 - distance for COSINE)
                if hasattr(doc, 'distance'):
                    memory["similarity"] = 1.0 - doc.distance
                else:
                    memory[
                        "similarity"] = 0.0  # Default if distance not available
                memories.append(memory)

            return memories

        except (ImportError, AttributeError) as e:
            # Fall back to manual similarity calculation if vector search is not available
            print(f"Firestore vector search not available: {e}")
            print("Falling back to manual similarity...")

            # Get all memories for the patient
            memories_ref = self.db.collection("patientMemoryVectors").document(
                patient_id).collection("chunks")
            memories = list(memories_ref.stream())

            # Calculate similarity for each memory
            memory_scores = []
            for memory_doc in memories:
                memory = memory_doc.to_dict()
                memory_vector = memory.get("vector")

                # Skip memories without a vector
                if not memory_vector:
                    continue

                # Check for dimension mismatch and handle it
                memory_dimension = len(memory_vector)
                query_dimension = len(query_embedding)

                if memory_dimension != query_dimension:
                    print(
                        f"Warning: Memory vector dimension ({memory_dimension}) doesn't match query dimension ({query_dimension})"
                    )

                    # Generate a new embedding for the memory's summary
                    if "summary" in memory:
                        try:
                            memory_vector = self.generate_embedding(
                                memory["summary"])
                        except Exception as e:
                            print(f"Error regenerating embedding: {e}")
                            continue
                    else:
                        continue

                # Calculate cosine similarity
                import numpy as np
                memory_vector = np.array(memory_vector)
                query_vector = np.array(query_embedding)

                try:
                    similarity = np.dot(memory_vector, query_vector) / (
                        np.linalg.norm(memory_vector) *
                        np.linalg.norm(query_vector))

                    # Add to list with similarity score
                    memory["similarity"] = float(similarity)
                    memory_scores.append(memory)
                except ValueError as e:
                    print(f"Error calculating similarity: {e}")
                    continue

            # Sort by similarity (highest first) and take top results
            memory_scores.sort(key=lambda x: x["similarity"], reverse=True)
            return memory_scores[:limit]

    def generate_response(self, patient_info: Dict[str, Any],
                          memories: List[Dict[str,
                                              Any]], user_message: str) -> str:
        """Generate a response using Gemini and retrieved memories"""
        # Format memories as context
        memories_context = ""
        for i, memory in enumerate(memories):
            mem_type = memory.get("metadata", {}).get("type", "memory")
            similarity = memory.get("similarity", 0.0)
            memories_context += f"{i+1}. {memory.get('summary', '')} (Type: {mem_type}, Relevance: {similarity:.2f})\n"

        # Generate prompt for Gemini
        prompt = f"""
        You are Mia, a friendly AI companion for {patient_info['name']}, who is an Alzheimer's patient.
        
        About {patient_info['name']}:
        - Hometown: {patient_info.get('hometown', 'unknown')}
        - Previous occupation: {patient_info.get('occupation', 'unknown')}
        - Hobbies: {', '.join(patient_info.get('hobbies', ['unknown']))}
        
        Use these relevant memories from {patient_info['name']} to inform your response:
        
        {memories_context}
        
        {patient_info['name']}'s message: "{user_message}"
        
        Respond in a warm, supportive manner. If the memories provide relevant information,
        use it naturally in your response without explicitly mentioning that you're using their memories.
        Keep your response conversational and compassionate, as you're speaking to someone with Alzheimer's.
        
        Your response:
        """

        # Generate response
        response = self.gemini_model.generate_content(prompt)
        return response.text

    def store_conversation(self, patient_id: str, user_message: str,
                           ai_response: str,
                           sentiment_data: Dict[str, Any]) -> Tuple[str, str]:
        """Store the conversation in Firestore"""
        # Get existing conversation
        conv_ref = self.db.collection("conversations").document(patient_id)
        conv_doc = conv_ref.get()

        if not conv_doc.exists:
            # Create new conversation document
            conv_ref.set({"messages": []})
            messages = []
        else:
            # Get existing messages
            messages = conv_doc.to_dict().get("messages", [])

        # Add user message
        current_time = datetime.now()
        user_msg_id = str(uuid.uuid4())
        user_message_obj = {
            "id": user_msg_id,
            "sender": "patient",
            "content": user_message,
            "timestamp": current_time,
            "sentiment": sentiment_data.get("category", "neutral"),
            "sentimentScore": sentiment_data.get("score", 0.0),
            "entities": sentiment_data.get("entities", {})
        }

        # Add AI response
        ai_msg_id = str(uuid.uuid4())
        ai_message_obj = {
            "id": ai_msg_id,
            "sender": "ai",
            "content": ai_response,
            "timestamp": current_time
        }

        # Update Firestore
        messages.append(user_message_obj)
        messages.append(ai_message_obj)
        conv_ref.update({"messages": messages})

        return user_msg_id, ai_msg_id

    def process_text_message(self, patient_id: str,
                             message: str) -> Dict[str, Any]:
        """Process a text message from a patient and generate a response"""
        try:
            # Get patient info
            patient_doc = self.db.collection("users").document(
                patient_id).get()
            if not patient_doc.exists:
                return {"error": "Patient not found"}

            patient_data = patient_doc.to_dict()
            patient_info = {
                "name":
                patient_data.get("displayName", "").split()[0],  # First name
                "hometown":
                patient_data.get("personalInfo",
                                 {}).get("hometown", "unknown"),
                "occupation":
                patient_data.get("personalInfo",
                                 {}).get("occupation", "unknown"),
                "hobbies":
                patient_data.get("personalInfo",
                                 {}).get("hobbies", ["unknown"])
            }

            # Analyze sentiment
            sentiment_data = self.analyze_sentiment(message)

            # Retrieve relevant memories
            memories = self.retrieve_memories(patient_id, message)

            # Generate AI response
            ai_response = self.generate_response(patient_info, memories,
                                                 message)

            # Convert to speech
            audio_response = self.text_to_speech(ai_response)
            audio_base64 = base64.b64encode(audio_response).decode('utf-8')

            # Store conversation
            user_msg_id, ai_msg_id = self.store_conversation(
                patient_id, message, ai_response, sentiment_data)

            return {
                "response":
                ai_response,
                "audioResponse":
                audio_base64,
                "messageIds": {
                    "userMessageId": user_msg_id,
                    "aiMessageId": ai_msg_id
                },
                "sentiment":
                sentiment_data.get("category"),
                "memories": [{
                    "summary": m.get("summary", ""),
                    "similarity": m.get("similarity", 0.0)
                } for m in memories]
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def process_audio_message(self, patient_id: str,
                              audio_content: bytes) -> Dict[str, Any]:
        """Process an audio message from a patient and generate a response"""
        try:
            # Convert speech to text
            message = self.speech_to_text(audio_content)

            if not message:
                return {"error": "Could not understand the audio message"}

            # Process the text message
            result = self.process_text_message(patient_id, message)

            # Add the transcribed message to the result
            result["message"] = message

            return result

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
