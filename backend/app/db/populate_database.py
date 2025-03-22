import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import uuid
import random
import numpy as np
from faker import Faker
import time
import hashlib
import json
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

# Import firebase config - assuming you have this file
from firebase import db

# Initialize Faker for generating realistic fake data
fake = Faker()


# Initialize Vertex AI for embeddings
def init_vertex_ai():
    try:
        # Initialize Vertex AI with your project
        aiplatform.init(project="memento-98a1c")
        embedding_model = TextEmbeddingModel.from_pretrained(
            "textembedding-gecko@latest")
        print("Successfully initialized Vertex AI")
        return embedding_model
    except Exception as e:
        print(f"Failed to initialize Vertex AI: {e}")
        print("Using simulated embeddings instead")
        return None


# Global embedding model
embedding_model = init_vertex_ai()


def generate_real_embedding(text):
    """Generate real embeddings using Vertex AI if available"""
    global embedding_model

    if embedding_model:
        try:
            embeddings = embedding_model.get_embeddings([text])
            return embeddings[0].values
        except Exception as e:
            print(f"Error generating real embedding: {e}")
            # Fall back to simulated embedding
            return generate_simulated_embedding(text)
    else:
        return generate_simulated_embedding(text)


def generate_simulated_embedding(text, dimension=128):
    """Generate a deterministic simulated embedding vector based on text content"""
    # Create a hash from the text
    text_hash = hashlib.md5(text.encode()).digest()

    # Use the hash to seed a random number generator
    np.random.seed(int.from_bytes(text_hash[:4], byteorder='big'))

    # Generate a simulated embedding vector
    vector = np.random.uniform(-1, 1, dimension).tolist()

    return vector


def generate_sample_users(num_caregivers=3, num_patients=10):
    """Generate sample caregiver and patient users with connections"""
    print("Generating sample users...")

    caregiver_ids = []
    patient_ids = []

    # Create caregivers
    for i in range(num_caregivers):
        caregiver_id = str(uuid.uuid4())
        caregiver_ids.append(caregiver_id)

        db.collection('users').document(caregiver_id).set({
            'username':
            f"caregiver{i+1}@example.com",
            'password':
            "hashed_password_would_go_here",  # In reality, you'd use proper auth
            'displayName':
            fake.name(),
            'type':
            "caregiver",
            'createdAt':
            firestore.SERVER_TIMESTAMP,
            'connections': {
                'patients': []  # Will be populated later
            }
        })

    # Create patients
    for i in range(num_patients):
        patient_id = str(uuid.uuid4())
        patient_ids.append(patient_id)

        # Assign to 1-2 random caregivers
        assigned_caregivers = random.sample(
            caregiver_ids, random.randint(1, min(2, len(caregiver_ids))))

        db.collection('users').document(patient_id).set({
            'username':
            f"patient{i+1}@example.com",
            'password':
            "hashed_password_would_go_here",  # In reality, you'd use proper auth
            'displayName':
            fake.name(),
            'type':
            "patient",
            'createdAt':
            firestore.SERVER_TIMESTAMP,
            'dateOfBirth':
            fake.date_of_birth(minimum_age=65,
                               maximum_age=90).strftime('%Y-%m-%d'),
            'medicalInfo': {
                'diagnosisDate':
                fake.date_time_between(start_date='-5y',
                                       end_date='now').strftime('%Y-%m-%d'),
                'alzheimerStage':
                random.choice(['Early', 'Middle', 'Late']),
                'medications':
                [fake.word() for _ in range(random.randint(1, 4))]
            },
            'personalInfo': {
                'familyMembers':
                [fake.name() for _ in range(random.randint(2, 5))],
                'hometown': fake.city(),
                'occupation': fake.job(),
                'hobbies': [fake.word() for _ in range(random.randint(1, 4))]
            },
            'connections': {
                'caregivers': assigned_caregivers
            }
        })

        # Update caregiver connections
        for caregiver_id in assigned_caregivers:
            caregiver_ref = db.collection('users').document(caregiver_id)
            caregiver_ref.update(
                {'connections.patients': firestore.ArrayUnion([patient_id])})

    print(f"Created {num_caregivers} caregivers and {num_patients} patients")
    return caregiver_ids, patient_ids


def generate_conversations(patient_ids, days_of_history=30):
    """Generate sample conversations between patients and AI chatbot"""
    print("Generating sample conversations...")

    # Common conversation topics for Alzheimer's patients
    topics = [
        "medication", "family", "memories", "daily activities", "meals",
        "sleep", "health", "mood", "weather", "hobbies"
    ]

    # More detailed conversation templates
    conversation_templates = [{
        'topic':
        'family',
        'ai_messages': [
            "How is your {relation} {name} doing?",
            "Do you remember when you last saw your {relation} {name}?",
            "Tell me about your {relation}. What are they like?",
            "Do you have any favorite memories with your {relation} {name}?"
        ],
        'patient_responses': [
            "My {relation} {name} is doing well. We talked on the phone last week.",
            "I think I saw {name} at {occasion}. They brought me some {item}.",
            "My {relation} {name} is very {trait}. They always {activity}.",
            "I can't quite remember when I last saw {name}.",
            "We used to {activity} together when they were younger."
        ]
    }, {
        'topic':
        'memories',
        'ai_messages': [
            "What's one of your favorite memories from your childhood?",
            "Tell me about your time working as a {occupation}.",
            "Do you remember your wedding day? What was it like?",
            "What was it like growing up in {hometown}?"
        ],
        'patient_responses': [
            "I remember when I was a child, we used to {activity} in {place}.",
            "When I worked as a {occupation}, I {accomplishment}. That was around {year}.",
            "My wedding day was {description}. We had the ceremony at {place}.",
            "Growing up in {hometown} was {description}. We lived near {landmark}.",
            "I'm having trouble remembering those details today."
        ]
    }, {
        'topic':
        'daily activities',
        'ai_messages': [
            "What did you have for breakfast today?",
            "Did you watch any TV shows or movies recently?",
            "Have you been sleeping well lately?",
            "Did you do any of your favorite hobbies today?"
        ],
        'patient_responses': [
            "I had {food} for breakfast. It was {quality}.",
            "I watched {show} earlier. It was about {topic}.",
            "My sleep has been {quality} lately. I {sleep_detail}.",
            "I spent some time {hobby} today. I've enjoyed that for {time_period}.",
            "I don't think I did much today. The days seem to blend together sometimes."
        ]
    }, {
        'topic':
        'medication',
        'ai_messages': [
            "Did you take your medication today?",
            "Have you been experiencing any side effects from your medication?",
            "Is your current medication helping you feel better?",
            "When is your next doctor's appointment?"
        ],
        'patient_responses': [
            "Yes, I took my medication {time}.",
            "I sometimes forget to take my pills. Did I take them today?",
            "The medication makes me feel {feeling}.",
            "I think my next appointment is {timeframe}. Dr. {name} is very {trait}.",
            "I'm not sure which medications I'm supposed to take."
        ]
    }]

    all_conversations = {}

    for patient_id in patient_ids:
        # Get patient info for personalization
        patient_doc = db.collection('users').document(
            patient_id).get().to_dict()
        patient_name = patient_doc['displayName'].split()[0]  # First name
        hometown = patient_doc.get('personalInfo',
                                   {}).get('hometown', fake.city())
        occupation = patient_doc.get('personalInfo',
                                     {}).get('occupation', fake.job())
        family_members = patient_doc.get('personalInfo',
                                         {}).get('familyMembers', [])

        conversation_messages = []

        # Generate conversations across multiple days
        for day in range(days_of_history):
            # Timestamp for this day (going backward from today)
            day_timestamp = datetime.now() - timedelta(days=days_of_history -
                                                       day)

            # 1-5 conversation exchanges per day
            num_exchanges = random.randint(1, 5)

            # Select a primary topic for today's conversation
            primary_template = random.choice(conversation_templates)

            for exchange in range(num_exchanges):
                # Sometimes switch topics during the conversation
                if random.random() < 0.3 and exchange > 0:
                    primary_template = random.choice(conversation_templates)

                # Personalize the message templates
                relation = random.choice([
                    'son', 'daughter', 'grandson', 'granddaughter', 'brother',
                    'sister', 'friend'
                ]) if family_members else ""
                family_name = random.choice(
                    family_members) if family_members else fake.name()

                replacements = {
                    '{name}':
                    family_name,
                    '{relation}':
                    relation,
                    '{occupation}':
                    occupation,
                    '{hometown}':
                    hometown,
                    '{place}':
                    fake.city(),
                    '{year}':
                    str(random.randint(1950, 2000)),
                    '{occasion}':
                    random.choice([
                        'Christmas', 'Thanksgiving', 'my birthday', 'Easter',
                        'the weekend'
                    ]),
                    '{item}':
                    random.choice(
                        ['flowers', 'cookies', 'a book', 'photos', 'a gift']),
                    '{trait}':
                    random.choice([
                        'kind', 'funny', 'serious', 'thoughtful', 'energetic'
                    ]),
                    '{activity}':
                    random.choice([
                        'go fishing', 'play cards', 'go to the movies',
                        'cook together', 'go for walks'
                    ]),
                    '{description}':
                    random.choice([
                        'wonderful', 'beautiful', 'simple', 'memorable',
                        'challenging'
                    ]),
                    '{landmark}':
                    random.choice([
                        'the park', 'the library', 'the river', 'downtown',
                        'the school'
                    ]),
                    '{food}':
                    random.choice(
                        ['eggs', 'toast', 'cereal', 'oatmeal', 'pancakes']),
                    '{quality}':
                    random.choice([
                        'good', 'delicious', 'okay', 'not great', 'wonderful'
                    ]),
                    '{show}':
                    random.choice([
                        'the news', 'a documentary', 'a game show', 'a movie',
                        'a sitcom'
                    ]),
                    '{topic}':
                    random.choice(
                        ['history', 'animals', 'travel', 'cooking', 'sports']),
                    '{sleep_detail}':
                    random.choice([
                        'wake up early', 'sleep through the night',
                        'have trouble falling asleep',
                        'take naps during the day'
                    ]),
                    '{hobby}':
                    random.choice([
                        'reading', 'gardening', 'knitting', 'watching TV',
                        'listening to music'
                    ]),
                    '{time_period}':
                    random.choice([
                        'years', 'decades', 'a long time', 'since I was young'
                    ]),
                    '{time}':
                    random.choice([
                        'this morning', 'after breakfast', 'with lunch',
                        'before bed'
                    ]),
                    '{feeling}':
                    random.choice([
                        'better', 'a bit dizzy', 'tired', 'about the same',
                        'less anxious'
                    ]),
                    '{timeframe}':
                    random.choice([
                        'next week', 'in two weeks', 'next month', 'soon',
                        'tomorrow'
                    ])
                }

                # AI message
                ai_message_template = random.choice(
                    primary_template['ai_messages'])
                ai_message = ai_message_template
                for key, value in replacements.items():
                    ai_message = ai_message.replace(key, value)

                ai_message_topics = [primary_template['topic']
                                     ] + random.sample(topics,
                                                       k=random.randint(0, 2))

                ai_timestamp = day_timestamp + timedelta(
                    hours=random.randint(8, 20), minutes=random.randint(0, 59))

                conversation_messages.append({
                    'id':
                    str(uuid.uuid4()),
                    'sender':
                    'ai',
                    'content':
                    ai_message,
                    'timestamp':
                    ai_timestamp,
                    'topics':
                    ai_message_topics,
                    'sentiment':
                    random.choice(['neutral', 'positive', 'question'])
                })

                # Patient response
                patient_response_template = random.choice(
                    primary_template['patient_responses'])
                patient_response = patient_response_template
                for key, value in replacements.items():
                    patient_response = patient_response.replace(key, value)

                # Random sentiment - weighted toward neutral/positive but some negative
                sentiment_choices = [
                    'neutral', 'neutral', 'positive', 'positive', 'negative',
                    'confused'
                ]
                sentiment_weights = [0.3, 0.3, 0.2, 0.1, 0.05, 0.05]

                patient_timestamp = ai_timestamp + timedelta(
                    minutes=random.randint(1, 5))

                conversation_messages.append({
                    'id':
                    str(uuid.uuid4()),
                    'sender':
                    'patient',
                    'content':
                    patient_response,
                    'timestamp':
                    patient_timestamp,
                    'topics':
                    ai_message_topics,  # Using the same topics as the AI message
                    'sentiment':
                    random.choices(sentiment_choices,
                                   weights=sentiment_weights)[0]
                })

        # Store the conversation
        db.collection('conversations').document(patient_id).set(
            {'messages': conversation_messages})

        # Store for later use in memory vectors
        all_conversations[patient_id] = conversation_messages

    print(
        f"Generated conversations for {len(patient_ids)} patients over {days_of_history} days"
    )
    return all_conversations


def generate_game_sessions(patient_ids, days_of_history=30):
    """Generate sample memory game sessions for patients"""
    print("Generating sample game sessions...")

    # Sample memory game questions
    question_templates = [{
        'category':
        'shortTerm',
        'questions': [
            "What did you have for breakfast today?",
            "What day of the week is it today?",
            "Who did you speak with this morning?",
            "What was the last TV show you watched?"
        ]
    }, {
        'category':
        'longTerm',
        'questions': [
            "What was your first job?", "What is your mother's maiden name?",
            "What was the name of your elementary school?",
            "Where did you go on your honeymoon?"
        ]
    }, {
        'category':
        'temporal',
        'questions': [
            "What month is it?", "What year is it?", "What season are we in?",
            "Is it morning, afternoon, or evening right now?"
        ]
    }, {
        'category':
        'spatial',
        'questions': [
            "Which room in your home has the TV?",
            "Where is the bathroom located in your home?",
            "What floor of the building do you live on?",
            "Which direction is the front door from your living room?"
        ]
    }]

    all_game_sessions = {}

    for patient_id in patient_ids:
        game_sessions = []

        # Generate game sessions across multiple days
        for day in range(days_of_history):
            # Not every day has a game session
            if random.random() < 0.7:  # 70% chance of having a game session
                continue

            # Timestamp for this day (going backward from today)
            day_timestamp = datetime.now() - timedelta(days=days_of_history -
                                                       day)
            session_start = day_timestamp + timedelta(
                hours=random.randint(9, 19), minutes=random.randint(0, 59))

            # Pick a random game category
            game_category = random.choice(question_templates)

            # Generate 3-7 questions for this game session
            question_count = random.randint(3, 7)
            question_data = []

            for _ in range(question_count):
                question_text = random.choice(game_category['questions'])

                # In a real app, correct answers would be known
                # Here we'll simulate random correctness
                is_correct = random.random() < (
                    0.7 if game_category['category'] == 'longTerm' else 0.5)

                question_data.append({
                    'questionId':
                    str(uuid.uuid4()),
                    'questionText':
                    question_text,
                    'memoryCategory':
                    game_category['category'],
                    'patientAnswer':
                    "Sample patient answer here",
                    'correctAnswer':
                    "Sample correct answer here",
                    'isCorrect':
                    is_correct,
                    'responseTimeSeconds':
                    random.randint(5, 30)
                })

            # Calculate overall score (0-100)
            correct_count = sum(1 for q in question_data if q['isCorrect'])
            score = int((correct_count / len(question_data)) * 100)

            session_duration = sum(q['responseTimeSeconds']
                                   for q in question_data) + random.randint(
                                       10, 30)
            session_end = session_start + timedelta(seconds=session_duration)

            # Create game session
            game_sessions.append({
                'id': str(uuid.uuid4()),
                'gameId': f"{game_category['category']}Game",
                'startedAt': session_start,
                'completedAt': session_end,
                'score': score,
                'questionData': question_data
            })

        # Store the game sessions
        db.collection('gameSessions').document(patient_id).set(
            {'sessions': game_sessions})

        all_game_sessions[patient_id] = game_sessions

    print(f"Generated game sessions for {len(patient_ids)} patients")
    return all_game_sessions


def extract_entities(text):
    """Extract potential people, places from text (simplified)"""
    # In a real app, you'd use NER models. This is a simplified version.
    words = text.split()

    # Look for capitalized words that might be names or places
    entities = [
        word.strip(',.!?;:()[]{}') for word in words
        if word and word[0].isupper() and len(word) > 1
        and word.strip(',.!?;:()[]{}').isalpha()
    ]

    return entities


def extract_keywords(text):
    """Extract potential keywords from text (simplified)"""
    # In a real app, you'd use keyword extraction models. This is simplified.
    common_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'of', 'to', 'in', 'for', 'with',
        'on', 'at', 'from', 'by', 'about', 'as', 'into', 'like', 'through',
        'after', 'over', 'between', 'out', 'against', 'during', 'without',
        'before', 'under', 'around', 'among', 'is', 'am', 'are', 'was', 'were',
        'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'shall', 'should', 'may', 'might', 'must', 'can',
        'could', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
        'her', 'us', 'them', 'this', 'that', 'these', 'those'
    }

    words = text.lower().split()
    keywords = [
        word.strip(',.!?;:()[]{}') for word in words
        if word.strip(',.!?;:()[]{}').isalpha() and word.strip(',.!?;:()[]{}')
        not in common_words and len(word.strip(',.!?;:()[]{}')) > 3
    ]

    # Remove duplicates and limit to 10 keywords
    unique_keywords = list(set(keywords))
    return unique_keywords[:10]


def generate_memory_vectors(patient_ids, conversations):
    """Generate memory vectors based on conversation data, with proper subcollections for vector search"""
    print("Generating memory vectors from conversations...")

    for patient_id in patient_ids:
        patient_conversations = conversations.get(patient_id, [])

        if not patient_conversations:
            continue

        # Get patient info for metadata
        patient_doc = db.collection('users').document(
            patient_id).get().to_dict()
        family_members = patient_doc.get('personalInfo',
                                         {}).get('familyMembers', [])

        # First create the patient document in patientMemoryVectors collection
        db.collection('patientMemoryVectors').document(patient_id).set({
            'patientId':
            patient_id,
            'totalMemories':
            0,  # Will update this at the end
            'lastUpdated':
            firestore.SERVER_TIMESTAMP
        })

        # Then get the chunks subcollection reference
        chunks_ref = db.collection('patientMemoryVectors').document(
            patient_id).collection('chunks')

        memory_count = 0

        # Process patient messages to create memory vectors
        patient_messages = [
            msg for msg in patient_conversations
            if msg.get('sender') == 'patient'
        ]

        # Group messages by day for context
        days = {}
        for msg in patient_messages:
            msg_timestamp = msg.get('timestamp')
            if isinstance(msg_timestamp, datetime):
                day_key = msg_timestamp.strftime('%Y-%m-%d')
                if day_key not in days:
                    days[day_key] = []
                days[day_key].append(msg)

        # Process conversation data by day
        for day, messages in days.items():
            if len(messages) < 1:
                continue

            # Combine messages if there are multiple in a day
            if len(messages) > 1:
                # Create a summary of the day's conversation
                message_contents = [msg.get('content', '') for msg in messages]
                daily_topics = []
                for msg in messages:
                    daily_topics.extend(msg.get('topics', []))

                summary = f"On {day}, the patient talked about: " + "; ".join(
                    message_contents[:3])

                # Extract entities and keywords
                entities = []
                keywords = []
                for content in message_contents:
                    entities.extend(extract_entities(content))
                    keywords.extend(extract_keywords(content))

                people = list(
                    set([
                        entity for entity in entities
                        if entity in family_members or random.random() < 0.3
                    ]))
                places = list(
                    set([
                        entity for entity in entities
                        if entity not in people and random.random() < 0.7
                    ]))
                topics = list(set(daily_topics))

                # Generate embedding vector
                vector = generate_real_embedding(summary)

                # Add document to chunks subcollection
                memory_id = str(uuid.uuid4())
                chunks_ref.document(memory_id).set({
                    'id':
                    memory_id,
                    'summary':
                    summary,
                    'sourceId':
                    f"conv_{day}",  # Reference to original conversation
                    'vector':
                    vector,
                    'keywords':
                    list(set(keywords))[:10],  # Limit to 10 unique keywords
                    'timestamp':
                    datetime.strptime(day, '%Y-%m-%d'),
                    'metadata': {
                        'people': people[:5],  # Limit to 5 people
                        'places': places[:3],  # Limit to 3 places
                        'topics': topics[:5],  # Limit to 5 topics
                        'type': 'conversation'
                    }
                })
                memory_count += 1
            else:
                # Process individual message
                msg = messages[0]
                content = msg.get('content', '')
                topics = msg.get('topics', [])

                # Extract entities and keywords
                entities = extract_entities(content)
                keywords = extract_keywords(content)

                people = [
                    entity for entity in entities
                    if entity in family_members or random.random() < 0.3
                ]
                places = [
                    entity for entity in entities
                    if entity not in people and random.random() < 0.7
                ]

                # Generate embedding vector
                vector = generate_real_embedding(content)

                # Add document to chunks subcollection
                memory_id = str(uuid.uuid4())
                chunks_ref.document(memory_id).set({
                    'id':
                    memory_id,
                    'summary':
                    content,
                    'sourceId':
                    msg.get('id', ''),  # Reference to original message
                    'vector':
                    vector,
                    'keywords':
                    keywords,
                    'timestamp':
                    msg.get('timestamp', datetime.strptime(day, '%Y-%m-%d')),
                    'metadata': {
                        'people': people[:5],  # Limit to 5 people
                        'places': places[:3],  # Limit to 3 places
                        'topics': topics[:5],  # Limit to 5 topics
                        'type': 'conversation'
                    }
                })
                memory_count += 1

        # Add some supplementary memories (not from conversations)
        additional_memory_types = ["photo", "diary", "medical", "biography"]

        for _ in range(random.randint(5, 15)):
            memory_type = random.choice(additional_memory_types)

            # Generate memory content based on type
            if memory_type == "photo":
                summary = f"Photo from {fake.date()} showing {random.choice(['family gathering', 'vacation', 'birthday', 'wedding', 'holiday'])}"
            elif memory_type == "diary":
                summary = f"Diary entry about {random.choice(['childhood memory', 'work experience', 'family event', 'travel'])}"
            elif memory_type == "medical":
                summary = f"Medical appointment on {fake.date()} with Dr. {fake.last_name()}"
            else:  # biography
                summary = f"Biographical detail about {random.choice(['childhood', 'education', 'career', 'marriage', 'retirement'])}"

            # Generate embedding vector
            vector = generate_real_embedding(summary)

            # Generate metadata
            people = []
            if random.random() < 0.7:  # 70% chance of including people
                people = random.sample(
                    family_members,
                    k=min(len(family_members), random.randint(
                        1, 3))) if family_members else [fake.name()]

            places = []
            if random.random() < 0.5:  # 50% chance of including places
                places = [fake.city()]

            topics = [fake.word() for _ in range(random.randint(1, 3))]

            # Add document to chunks subcollection
            memory_id = str(uuid.uuid4())
            chunks_ref.document(memory_id).set({
                'id':
                memory_id,
                'summary':
                summary,
                'sourceId':
                str(uuid.uuid4()),  # Reference to original content
                'vector':
                vector,
                'keywords':
                extract_keywords(summary),
                'timestamp':
                fake.date_time_between(start_date='-50y', end_date='now'),
                'metadata': {
                    'people': people,
                    'places': places,
                    'topics': topics,
                    'type': memory_type
                }
            })
            memory_count += 1

        # Update the total count in the patient document
        db.collection('patientMemoryVectors').document(patient_id).update(
            {'totalMemories': memory_count})

    print(f"Generated memory vectors for {len(patient_ids)} patients")


def setup_vector_search():
    """Set up vector search indexes for the patientMemoryVectors collection"""
    try:
        from google.cloud.firestore_v1.vector_search import VectorSearchOptions

        # Create vector search options
        vector_search_options = VectorSearchOptions(
            dimensions=768,  # Update this to match your actual vector dimension
            distance_measure="COSINE",
            field_path="vector")

        # Apply to all patient vector collections
        patients = db.collection("patientMemoryVectors").stream()

        for patient_doc in patients:
            patient_id = patient_doc.id

            # Create vector index on chunks subcollection
            chunks_ref = db.collection("patientMemoryVectors").document(
                patient_id).collection("chunks")

            try:
                chunks_ref.create_vector_index(vector_search_options)
                print(f"Created vector index for patient {patient_id}")
            except Exception as e:
                print(
                    f"Failed to create vector index for patient {patient_id}: {e}"
                )

        print("Vector search setup completed")
    except Exception as e:
        print(f"Vector search setup failed: {e}")
        print(
            "You may need to set up vector search manually in the GCP console")


def test_vector_search(patient_id, query_text="Tell me about my family"):
    """Test vector search functionality"""
    try:
        from google.cloud.firestore_v1 import VectorQuery

        print(
            f"Testing vector search for patient {patient_id} with query: '{query_text}'"
        )

        # Generate query vector
        query_vector = generate_real_embedding(query_text)

        # Build vector query
        vector_query = (VectorQuery(
            dimensions=len(query_vector),
            distance_type=VectorQuery.DistanceType.COSINE,
            vector=query_vector,
        ).with_field_path("vector").build())

        # Perform search
        chunks_ref = db.collection("patientMemoryVectors").document(
            patient_id).collection("chunks")

        results = chunks_ref.find(vector_query=vector_query, num_to_return=5)

        # Print results
        print("\nSearch results:")
        for i, doc in enumerate(results):
            data = doc.to_dict()
            print(
                f"{i+1}. {data.get('summary', 'No summary')} (Score: {doc.distance})"
            )

    except ImportError:
        print(
            "Vector search classes not available. Make sure you're using the latest Firebase Admin SDK"
        )
    except Exception as e:
        print(f"Vector search test failed: {e}")


def export_sample_ids(caregiver_ids, patient_ids):
    """Export sample IDs to a JSON file for testing"""
    try:
        sample_data = {
            "caregivers": caregiver_ids[:2],  # First 2 caregivers
            "patients": patient_ids[:3],  # First 3 patients
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Convert datetime objects to strings for JSON serialization
        def json_serial(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        with open("sample_ids.json", "w") as f:
            json.dump(sample_data, f, default=json_serial, indent=2)

        print(f"Sample IDs exported to sample_ids.json")
    except Exception as e:
        print(f"Failed to export sample IDs: {e}")


def populate_database():
    """Main function to populate the entire database"""
    start_time = time.time()

    # Check if database already has data to avoid duplicate entries
    users_count = len(list(db.collection('users').limit(1).stream()))
    if users_count > 0:
        print(
            "Database already contains data. Aborting to prevent duplication.")
        print("If you want to repopulate, first clear the database.")
        return

    # Generate all data
    caregiver_ids, patient_ids = generate_sample_users()
    conversations = generate_conversations(patient_ids)
    game_sessions = generate_game_sessions(patient_ids)
    generate_memory_vectors(patient_ids, conversations)

    # Try to set up vector search indexes
    setup_vector_search()

    # Export sample IDs for testing
    export_sample_ids(caregiver_ids, patient_ids)

    # Test vector search with a sample patient
    if patient_ids:
        test_vector_search(patient_ids[0])

    end_time = time.time()
    print(
        f"Database populated successfully in {end_time - start_time:.2f} seconds!"
    )
    print("\nSample IDs for testing:")
    print(f"Caregiver ID: {caregiver_ids[0]}")
    print(f"Patient ID: {patient_ids[0]}")
    print("\nNote: More sample IDs are available in the sample_ids.json file")


def clear_database():
    """Clear all collections from the database - USE WITH CAUTION"""
    print("WARNING: This will delete ALL data in the database.")
    confirmation = input("Type 'DELETE' to confirm: ")

    if confirmation != "DELETE":
        print("Operation canceled.")
        return

    collections = [
        'users', 'conversations', 'gameSessions', 'patientMemoryVectors'
    ]

    for collection_name in collections:
        # Get all documents in the collection
        docs = db.collection(collection_name).stream()

        for doc in docs:
            # For patientMemoryVectors, need to delete chunks subcollection first
            if collection_name == 'patientMemoryVectors':
                chunks = db.collection(collection_name).document(
                    doc.id).collection('chunks').stream()
                for chunk in chunks:
                    chunk.reference.delete()

            # Delete the document
            doc.reference.delete()

        print(f"Cleared collection: {collection_name}")

    print("Database cleared successfully")


def print_menu():
    """Display a menu of options"""
    print("\nMEMENTO DATABASE UTILITY")
    print("=======================")
    print("1. Populate database")
    print("2. Clear database")
    print("3. Test vector search")
    print("4. Exit")

    choice = input("\nEnter choice (1-4): ")

    if choice == '1':
        populate_database()
    elif choice == '2':
        clear_database()
    elif choice == '3':
        patient_id = input("Enter patient ID: ")
        query = input("Enter search query: ")
        test_vector_search(patient_id, query)
    elif choice == '4':
        print("Exiting.")
        return
    else:
        print("Invalid choice")

    input("\nPress Enter to continue...")
    print_menu()


if __name__ == "__main__":
    print("Memento Database Population Script")
    print("=================================")

    # Command-line arguments handling
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "populate":
            populate_database()
        elif sys.argv[1] == "clear":
            clear_database()
        elif sys.argv[1] == "test" and len(sys.argv) > 2:
            test_vector_search(
                sys.argv[2], sys.argv[3]
                if len(sys.argv) > 3 else "Tell me about my family")
        else:
            print(
                "Usage: python populate_database.py [populate|clear|test <patient_id> <query>]"
            )
    else:
        # Interactive mode
        print_menu()
