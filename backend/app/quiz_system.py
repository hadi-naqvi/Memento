import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Google Cloud imports
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel


class MementoQuizSystem:
    """Quiz generation system for Memento app using RAG to create personalized memory quizzes"""

    def __init__(self, project_id=None, db=None):
        """Initialize the Quiz system with Google Cloud clients"""
        # Get project ID from environment variable if not provided
        self.project_id = project_id or os.environ.get("GCP_PROJECT_ID")
        if not self.project_id:
            print("Warning: GCP_PROJECT_ID not set. Using 'test-project-id'")
            self.project_id = "test-project-id"

        try:
            # Initialize Vertex AI
            aiplatform.init(project=self.project_id)

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
                f"Memento Quiz System initialized with project ID: {self.project_id}"
            )
        except Exception as e:
            print(f"Error initializing Quiz system: {e}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        """Generate text embeddings using Vertex AI"""
        embeddings = self.embedding_model.get_embeddings([text])
        return embeddings[0].values

    def retrieve_memories(self,
                          patient_id: str,
                          query_text: str,
                          limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant memories for a patient based on query text"""
        # Generate query embedding
        query_embedding = self.generate_embedding(query_text)

        try:
            # Try using Firestore's vector search
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
                # Add the similarity score
                if hasattr(doc, 'distance'):
                    memory["similarity"] = 1.0 - doc.distance
                else:
                    memory["similarity"] = 0.0
                memories.append(memory)

            return memories

        except (ImportError, AttributeError) as e:
            # Fall back to manual similarity calculation
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

    def retrieve_conversations(self,
                               patient_id: str,
                               days_limit: int = 30,
                               count_limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent conversations for a patient"""
        try:
            # Get conversation collection
            conv_ref = self.db.collection("conversations").document(patient_id)
            conv_doc = conv_ref.get()

            if not conv_doc.exists:
                return []

            # Get messages
            all_messages = conv_doc.to_dict().get("messages", [])

            # Filter by date if needed
            if days_limit > 0:
                cutoff_date = datetime.now() - datetime.timedelta(
                    days=days_limit)
                filtered_messages = [
                    msg for msg in all_messages
                    if 'timestamp' in msg and msg['timestamp'] >= cutoff_date
                ]
            else:
                filtered_messages = all_messages

            # Sort by timestamp (newest first) and limit count
            filtered_messages.sort(
                key=lambda x: x.get('timestamp', datetime.min), reverse=True)

            return filtered_messages[:count_limit]

        except Exception as e:
            print(f"Error retrieving conversations: {e}")
            return []

    def generate_quiz(self,
                      patient_id: str,
                      quiz_type: str = "mixed",
                      question_count: int = 5) -> Dict[str, Any]:
        """
        Generate a personalized quiz based on patient memories and conversations
        
        Args:
            patient_id: ID of the patient
            quiz_type: Type of quiz ('memory', 'conversation', 'mixed', 'general')
            question_count: Number of questions to generate
            
        Returns:
            Dictionary containing quiz data
        """
        try:
            # Get patient info
            patient_doc = self.db.collection("users").document(
                patient_id).get()
            if not patient_doc.exists:
                return {"error": "Patient not found"}

            patient_data = patient_doc.to_dict()
            first_name = patient_data.get("displayName", "").split()[0]

            # Collect content for question generation
            memories = []
            conversations = []

            # Get memories based on quiz type
            if quiz_type in ["memory", "mixed"]:
                # Retrieve some random memories as seeds
                memory_docs = self.db.collection("patientMemories").document(
                    patient_id).get().to_dict()

                if memory_docs and "memories" in memory_docs:
                    all_memories = memory_docs["memories"]
                    # Take up to 10 random memories
                    import random
                    sample_size = min(10, len(all_memories))
                    memory_samples = random.sample(all_memories, sample_size)

                    for memory in memory_samples:
                        memories.append({
                            "title":
                            memory.get("title", ""),
                            "content":
                            memory.get("content", ""),
                            "type":
                            memory.get("metadata", {}).get("type", "memory"),
                            "people":
                            memory.get("metadata", {}).get("people", []),
                            "places":
                            memory.get("metadata", {}).get("places", [])
                        })

            # Get conversations based on quiz type
            if quiz_type in ["conversation", "mixed"]:
                recent_messages = self.retrieve_conversations(patient_id,
                                                              days_limit=30,
                                                              count_limit=50)

                # Process messages to extract relevant information
                user_messages = [
                    msg for msg in recent_messages
                    if msg.get("sender", "") == "patient"
                ]

                # Take up to 20 recent user messages
                for msg in user_messages[:20]:
                    conversations.append({
                        "content": msg.get("content", ""),
                        "timestamp": msg.get("timestamp", ""),
                        "topics": msg.get("topics", [])
                    })

            # Prepare prompt for quiz generation
            prompt = self._create_quiz_prompt(first_name, memories,
                                              conversations, quiz_type,
                                              question_count)

            # Generate questions using Gemini
            response = self.gemini_model.generate_content(prompt)

            # Parse the response into structured quiz data
            quiz_data = self._parse_quiz_response(response.text)

            # Create and store quiz session
            quiz_id = str(uuid.uuid4())
            quiz_session = {
                "id": quiz_id,
                "patientId": patient_id,
                "quizType": quiz_type,
                "createdAt": datetime.now(),
                "questions": quiz_data,
                "status": "active",
                "patientName": first_name
            }

            # Store in database
            self.db.collection("gameSessions").document(quiz_id).set(
                quiz_session)

            return {
                "quiz_id": quiz_id,
                "quiz_type": quiz_type,
                "question_count": len(quiz_data),
                "questions": quiz_data
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def _create_quiz_prompt(self, patient_name: str, memories: List[Dict[str,
                                                                         Any]],
                            conversations: List[Dict[str, Any]],
                            quiz_type: str, question_count: int) -> str:
        """Create a prompt for quiz generation"""

        # Prepare memories context
        memory_context = ""
        for i, memory in enumerate(memories):
            memory_context += f"Memory {i+1}. Title: {memory.get('title', 'Untitled')}\n"
            memory_context += f"Content: {memory.get('content', '')}\n"
            memory_context += f"People mentioned: {', '.join(memory.get('people', []))}\n"
            memory_context += f"Places mentioned: {', '.join(memory.get('places', []))}\n\n"

        # Prepare conversations context
        conversation_context = ""
        for i, convo in enumerate(conversations):
            conversation_context += f"Conversation {i+1}: {convo.get('content', '')}\n"
            if convo.get('topics'):
                conversation_context += f"Topics: {', '.join(convo.get('topics', []))}\n"
            conversation_context += "\n"

        # Build the prompt
        prompt = f"""
        You are a cognitive health assistant creating a personalized memory quiz for {patient_name}, 
        who is an Alzheimer's or dementia patient. This quiz will help exercise their memory recall.
        
        Please create {question_count} multiple-choice questions based on the following information 
        about {patient_name}:
        
        """

        if quiz_type == "memory" or quiz_type == "mixed":
            prompt += f"""
            MEMORIES:
            {memory_context}
            """

        if quiz_type == "conversation" or quiz_type == "mixed":
            prompt += f"""
            RECENT CONVERSATIONS:
            {conversation_context}
            """

        if quiz_type == "general":
            prompt += f"""
            This should be a general knowledge quiz with simple questions that most older adults 
            would know, focusing on long-term memory recall rather than recent events.
            """

        prompt += f"""
        INSTRUCTIONS:
        1. Create {question_count} multiple-choice questions that would help exercise {patient_name}'s memory
        2. Each question should have 4 possible answers, with only one being correct
        3. Questions should be gentle and supportive, not frustrating
        4. Include a mix of difficulty levels but keep most questions relatively easy
        5. For each question, also provide a brief explanation of the correct answer that can be shown to {patient_name}
        6. Format each question using the following structure:
        
        Q1: [Question text]
        A. [First option]
        B. [Second option]
        C. [Third option]
        D. [Fourth option]
        CORRECT: [Correct option letter]
        EXPLANATION: [Brief explanation]
        CATEGORY: [Category of memory being tested: personal, temporal, spatial, factual, etc.]
        
        Return only the formatted questions without any other text.
        """

        return prompt

    def _parse_quiz_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse the model's response into structured quiz data"""

        questions = []
        current_question = {}

        # Split the response into lines
        lines = response_text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse question
            if line.startswith('Q') and ':' in line:
                # Save the previous question if it exists
                if current_question and 'text' in current_question:
                    questions.append(current_question)

                # Start a new question
                current_question = {
                    'options': [],
                    'text': line.split(':', 1)[1].strip(),
                    'id': str(uuid.uuid4())
                }

            # Parse options
            elif line.startswith(('A.', 'B.', 'C.', 'D.')):
                option_letter = line[0]
                option_text = line[2:].strip()
                current_question.setdefault('options', []).append({
                    'id':
                    option_letter,
                    'text':
                    option_text
                })

            # Parse correct answer
            elif line.startswith('CORRECT:'):
                current_question['correctAnswer'] = line.split(':',
                                                               1)[1].strip()

            # Parse explanation
            elif line.startswith('EXPLANATION:'):
                current_question['explanation'] = line.split(':', 1)[1].strip()

            # Parse category
            elif line.startswith('CATEGORY:'):
                current_question['category'] = line.split(
                    ':', 1)[1].strip().lower()

        # Add the last question
        if current_question and 'text' in current_question:
            questions.append(current_question)

        return questions

    def record_quiz_answer(self, quiz_id: str, question_id: str,
                           selected_option: str) -> Dict[str, Any]:
        """
        Record a patient's answer to a quiz question
        
        Args:
            quiz_id: ID of the quiz session
            question_id: ID of the question being answered
            selected_option: The option selected by the patient (A, B, C, or D)
            
        Returns:
            Dictionary with answer result
        """
        try:
            # Get the quiz session
            quiz_ref = self.db.collection("gameSessions").document(quiz_id)
            quiz_doc = quiz_ref.get()

            if not quiz_doc.exists:
                return {"error": "Quiz session not found"}

            quiz_data = quiz_doc.to_dict()

            # Find the question
            questions = quiz_data.get("questions", [])
            question = next(
                (q for q in questions if q.get("id") == question_id), None)

            if not question:
                return {"error": "Question not found in this quiz"}

            # Check if this question has already been answered
            answers = quiz_data.get("answers", [])
            existing_answer = next(
                (a for a in answers if a.get("questionId") == question_id),
                None)

            if existing_answer:
                return {"error": "This question has already been answered"}

            # Record the answer
            correct_option = question.get("correctAnswer")
            is_correct = selected_option == correct_option

            answer_record = {
                "questionId": question_id,
                "selectedOption": selected_option,
                "correctOption": correct_option,
                "isCorrect": is_correct,
                "timestamp": datetime.now()
            }

            # Update the quiz session
            answers.append(answer_record)
            quiz_ref.update({"answers": answers})

            # Check if all questions have been answered
            if len(answers) == len(questions):
                # Calculate score
                correct_count = sum(1 for a in answers
                                    if a.get("isCorrect", False))
                score = int((correct_count / len(questions)) * 100)

                # Update quiz status and score
                quiz_ref.update({
                    "status": "completed",
                    "completedAt": datetime.now(),
                    "score": score
                })

                # Update patient's memory score in user profile (optional)
                patient_id = quiz_data.get("patientId")
                if patient_id:
                    # Get recent quiz scores (last 5)
                    recent_quizzes = self.db.collection("gameSessions") \
                        .where("patientId", "==", patient_id) \
                        .where("status", "==", "completed") \
                        .order_by("completedAt", direction="DESCENDING") \
                        .limit(5) \
                        .stream()

                    scores = [
                        q.to_dict().get("score", 0) for q in recent_quizzes
                    ]
                    avg_score = sum(scores) / len(scores) if scores else 0

                    # Update user's memory score
                    self.db.collection("users").document(patient_id).update(
                        {"memoryScore": int(avg_score)})

            # Return the result
            return {
                "isCorrect": is_correct,
                "correctOption": correct_option,
                "explanation": question.get("explanation", ""),
                "allQuestionsAnswered": len(answers) == len(questions)
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def get_quiz_session(self, quiz_id: str) -> Dict[str, Any]:
        """
        Get the details of a quiz session
        
        Args:
            quiz_id: ID of the quiz session
            
        Returns:
            Dictionary with quiz session data
        """
        try:
            # Get the quiz session
            quiz_ref = self.db.collection("gameSessions").document(quiz_id)
            quiz_doc = quiz_ref.get()

            if not quiz_doc.exists:
                return {"error": "Quiz session not found"}

            quiz_data = quiz_doc.to_dict()

            # Clean up timestamps for JSON serialization
            if "createdAt" in quiz_data and isinstance(quiz_data["createdAt"],
                                                       datetime):
                quiz_data["createdAt"] = quiz_data["createdAt"].isoformat()
            if "completedAt" in quiz_data and isinstance(
                    quiz_data["completedAt"], datetime):
                quiz_data["completedAt"] = quiz_data["completedAt"].isoformat()

            # Clean up answer timestamps
            for answer in quiz_data.get("answers", []):
                if "timestamp" in answer and isinstance(
                        answer["timestamp"], datetime):
                    answer["timestamp"] = answer["timestamp"].isoformat()

            return quiz_data

        except Exception as e:
            return {"error": str(e)}

    def get_patient_quiz_history(self,
                                 patient_id: str,
                                 limit: int = 10) -> Dict[str, Any]:
        """
        Get quiz history for a patient
        
        Args:
            patient_id: ID of the patient
            limit: Maximum number of quiz sessions to return
            
        Returns:
            Dictionary with quiz history data
        """
        try:
            # Query for quiz sessions
            quiz_query = self.db.collection("gameSessions") \
                .where("patientId", "==", patient_id) \
                .order_by("createdAt", direction="DESCENDING") \
                .limit(limit)

            quiz_docs = quiz_query.stream()

            # Process results
            quizzes = []
            for doc in quiz_docs:
                quiz_data = doc.to_dict()

                # Clean up timestamps for JSON serialization
                if "createdAt" in quiz_data and isinstance(
                        quiz_data["createdAt"], datetime):
                    quiz_data["createdAt"] = quiz_data["createdAt"].isoformat()
                if "completedAt" in quiz_data and isinstance(
                        quiz_data["completedAt"], datetime):
                    quiz_data["completedAt"] = quiz_data[
                        "completedAt"].isoformat()

                # Simplify the data structure for the list view
                simplified_quiz = {
                    "id": quiz_data.get("id"),
                    "quizType": quiz_data.get("quizType"),
                    "createdAt": quiz_data.get("createdAt"),
                    "completedAt": quiz_data.get("completedAt"),
                    "status": quiz_data.get("status"),
                    "score": quiz_data.get("score", 0),
                    "questionCount": len(quiz_data.get("questions", [])),
                    "answeredCount": len(quiz_data.get("answers", []))
                }

                quizzes.append(simplified_quiz)

            # Get some statistics
            total_quizzes_query = self.db.collection("gameSessions") \
                .where("patientId", "==", patient_id) \
                .count()

            total_quizzes = total_quizzes_query.get()[0][0]

            completed_quizzes_query = self.db.collection("gameSessions") \
                .where("patientId", "==", patient_id) \
                .where("status", "==", "completed") \
                .count()

            completed_quizzes = completed_quizzes_query.get()[0][0]

            # Calculate score trends if there are completed quizzes
            score_trends = []
            if completed_quizzes > 0:
                score_query = self.db.collection("gameSessions") \
                    .where("patientId", "==", patient_id) \
                    .where("status", "==", "completed") \
                    .order_by("completedAt") \
                    .limit(20) \
                    .stream()

                for doc in score_query:
                    quiz_data = doc.to_dict()
                    if "score" in quiz_data and "completedAt" in quiz_data:
                        completed_at = quiz_data["completedAt"]
                        if isinstance(completed_at, datetime):
                            completed_at = completed_at.isoformat()

                        score_trends.append({
                            "date":
                            completed_at,
                            "score":
                            quiz_data["score"],
                            "quizType":
                            quiz_data.get("quizType")
                        })

            return {
                "quizzes": quizzes,
                "totalQuizzes": total_quizzes,
                "completedQuizzes": completed_quizzes,
                "scoreTrends": score_trends
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
