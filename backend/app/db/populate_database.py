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
import sys
from datetime import datetime, timedelta

# Try importing Vertex AI libraries, but continue if not available
try:
    from google.cloud import aiplatform
    from vertexai.language_models import TextEmbeddingModel
    vertex_available = True
except ImportError:
    print(
        "Vertex AI libraries not available. Using simulated embeddings only.")
    vertex_available = False

# Initialize Faker for generating realistic fake data
fake = Faker()

# Try importing firebase config
try:
    from firebase import db
    print("Successfully imported Firebase database connection")
except ImportError:
    print("Error: Could not import db from firebase module.")
    print("Please create a firebase.py file with your Firebase configuration.")
    sys.exit(1)


# Initialize Vertex AI for embeddings
def init_vertex_ai():
    if not vertex_available:
        print("Vertex AI libraries not available. Using simulated embeddings.")
        return None

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


def generate_sample_users(num_users=3):
    """Generate sample users with reminders"""
    print("Generating sample users...")

    user_ids = []

    # Diagnosis types
    diagnosis_types = [
        "Alzheimer's", "Dementia", "Mild Cognitive Impairment", "Memory Loss"
    ]

    # Create users
    for i in range(num_users):
        user_id = str(uuid.uuid4())
        user_ids.append(user_id)

        # Generate random scores
        medication_adherence = random.randint(60, 95)
        memory_score = random.randint(50, 90)
        daily_completed = random.randint(2, 5)
        daily_total = 5

        # Generate reminders (3 per user)
        reminders = []
        for j in range(3):
            # Set up various reminder types
            reminder_types = [{
                "title":
                "Take medication",
                "description":
                f"Take {random.choice(['morning', 'afternoon', 'evening'])} {random.choice(['pills', 'medication', 'dose'])}",
                "imageUrl":
                f"https://example.com/med_reminder_{j+1}.jpg"
            }, {
                "title":
                "Doctor appointment",
                "description":
                f"Visit Dr. {fake.last_name()} for {random.choice(['check-up', 'follow-up', 'consultation'])}",
                "imageUrl":
                f"https://example.com/appointment_{j+1}.jpg"
            }, {
                "title":
                "Family call",
                "description":
                f"Call {random.choice(['son', 'daughter', 'grandchild'])} {fake.first_name()}",
                "imageUrl":
                f"https://example.com/family_call_{j+1}.jpg"
            }, {
                "title":
                "Memory exercise",
                "description":
                "Complete today's memory training session",
                "imageUrl":
                f"https://example.com/memory_exercise_{j+1}.jpg"
            }, {
                "title": "Meal time",
                "description":
                f"Time for {random.choice(['breakfast', 'lunch', 'dinner'])}",
                "imageUrl": f"https://example.com/meal_{j+1}.jpg"
            }]

            # Select a random reminder type
            reminder_type = random.choice(reminder_types)

            # Create the reminder with timestamp a few days in the past, present, or future
            days_offset = random.randint(-3, 7)
            reminder_time = datetime.now() + timedelta(
                days=days_offset,
                hours=random.randint(8, 20),
                minutes=random.randint(0, 59))

            # Reminders in the past are more likely to be completed
            is_completed = days_offset < 0 and random.random() < 0.8

            reminders.append({
                "id": str(uuid.uuid4()),
                "title": reminder_type["title"],
                "description": reminder_type["description"],
                "timestamp": reminder_time,
                "isCompleted": is_completed,
                "imageUrl": reminder_type["imageUrl"]
            })

        # Generate a birth date as a datetime object, not a date object
        # This is the key fix - convert faker's date_of_birth to a datetime
        birth_date = fake.date_of_birth(minimum_age=65, maximum_age=90)
        birth_datetime = datetime.combine(birth_date, datetime.min.time())

        # Create the user document
        db.collection('users').document(user_id).set({
            'username':
            f"user{i+1}",
            'email':
            f"user{i+1}@example.com",
            'displayName':
            fake.name(),
            'birthDate':
            birth_datetime,  # Using datetime object instead of date
            'diagnosisType':
            random.choice(diagnosis_types),
            'profileImageUrl':
            f"https://example.com/profile_{i+1}.jpg",
            'createdAt':
            firestore.SERVER_TIMESTAMP,
            'medicationAdherence':
            medication_adherence,
            'memoryScore':
            memory_score,
            'dailyQuestionsCompleted':
            daily_completed,
            'dailyQuestionsTotal':
            daily_total,
            'reminders':
            reminders
        })

    print(f"Created {num_users} users with reminders")
    return user_ids


def generate_conversations(user_ids, days_of_history=30):
    """Generate sample conversations between users and AI chatbot"""
    print("Generating sample conversations...")

    # Common conversation topics for users with memory issues
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

    for user_id in user_ids:
        # Get user info for personalization
        user_doc = db.collection('users').document(user_id).get().to_dict()
        user_name = user_doc['displayName'].split()[0]  # First name

        # Generate some random personal info for conversation context
        hometown = fake.city()
        occupation = fake.job()
        family_members = [fake.name() for _ in range(random.randint(2, 5))]

        conversation_messages = []

        # Generate conversations across multiple days
        for day in range(days_of_history):
            # Not every day has conversations
            if random.random() < 0.3:  # 70% chance of having conversations
                continue

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
                ])
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
                    'id': str(uuid.uuid4()),
                    'sender': 'ai',
                    'content': ai_message,
                    'timestamp': ai_timestamp,
                    'topics': ai_message_topics
                })

                # Patient response
                patient_response_template = random.choice(
                    primary_template['patient_responses'])
                patient_response = patient_response_template
                for key, value in replacements.items():
                    patient_response = patient_response.replace(key, value)

                patient_timestamp = ai_timestamp + timedelta(
                    minutes=random.randint(1, 5))

                conversation_messages.append({
                    'id': str(uuid.uuid4()),
                    'sender': 'patient',
                    'content': patient_response,
                    'timestamp': patient_timestamp,
                    'topics':
                    ai_message_topics  # Using the same topics as the AI message
                })

        # Store the conversation
        db.collection('conversations').document(user_id).set(
            {'messages': conversation_messages})

    print(f"Generated conversations for {len(user_ids)} users")
    return True


def generate_game_sessions(user_ids, days_of_history=30):
    """Generate sample memory game sessions for users"""
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

    for user_id in user_ids:
        game_sessions = []

        # Generate game sessions across multiple days
        for day in range(days_of_history):
            # Not every day has a game session
            if random.random() < 0.7:  # 30% chance of having a game session
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
        db.collection('gameSessions').document(user_id).set(
            {'sessions': game_sessions})

    print(f"Generated game sessions for {len(user_ids)} users")
    return True


def generate_patient_memories(user_ids):
    """Generate sample memories for each patient"""
    print("Generating patient memories...")

    memory_types = ["photo", "diary", "medical", "biography", "milestone"]

    for user_id in user_ids:
        user_doc = db.collection('users').document(user_id).get().to_dict()
        user_name = user_doc['displayName']

        # Generate some context data for memories
        family_names = [fake.name() for _ in range(5)]
        places = [fake.city() for _ in range(5)]

        # Create between 5-10 memories per user
        memories = []
        for i in range(random.randint(5, 10)):
            memory_type = random.choice(memory_types)

            # Generate title and content based on type
            if memory_type == "photo":
                title = f"Family photo from {fake.year()}"
                content = f"A {random.choice(['color', 'black and white'])} photograph showing {user_name} with {random.choice(family_names)} at {random.choice(places)}. {random.choice(['Everyone is smiling.', 'It was a special occasion.', 'The weather was beautiful that day.'])}"
                image_url = f"https://example.com/memory_photos/{i+1}.jpg"
            elif memory_type == "diary":
                title = f"Journal entry - {fake.date_time_between(start_date='-50y', end_date='-1y').strftime('%B %Y')}"
                content = f"Today I went to {random.choice(places)} with {random.choice(family_names)}. We {random.choice(['had lunch at a nice restaurant', 'went for a walk in the park', 'visited the museum', 'saw an old friend'])}. {fake.paragraph(nb_sentences=2)}"
                image_url = f"https://example.com/diary_pages/{i+1}.jpg"
            elif memory_type == "medical":
                title = f"Medical record - {fake.date_time_between(start_date='-10y', end_date='-1y').strftime('%B %d, %Y')}"
                content = f"Appointment with Dr. {fake.last_name()} at {fake.company()} Medical Center. {random.choice(['Regular checkup', 'Follow-up appointment', 'Consultation about symptoms'])}: {fake.paragraph(nb_sentences=1)}"
                image_url = f"https://example.com/medical_records/{i+1}.jpg"
            elif memory_type == "biography":
                title = f"Life milestone - {random.choice(['Childhood', 'School years', 'First job', 'Marriage', 'Career', 'Retirement'])}"
                content = f"{fake.paragraph(nb_sentences=3)} This was during my time in {random.choice(places)}."
                image_url = f"https://example.com/biography/{i+1}.jpg"
            else:  # milestone
                title = f"Important event - {fake.date_time_between(start_date='-50y', end_date='-1y').strftime('%Y')}"
                content = f"{random.choice(['Wedding day', 'Birth of my child', 'Graduation', 'First house', 'Retirement party'])} in {random.choice(places)}. {fake.paragraph(nb_sentences=2)}"
                image_url = f"https://example.com/milestone/{i+1}.jpg"

            # Generate keywords
            keywords = list(
                set([
                    word for word in content.split()
                    if len(word) > 4 and word.isalpha()
                ][:10]))

            # Create people, places, topics metadata
            people = random.sample(family_names, k=random.randint(1, 3))
            memory_places = random.sample(places, k=random.randint(1, 2))
            topics = random.sample([
                "family", "travel", "health", "celebration", "work",
                "education", "hobby"
            ],
                                   k=random.randint(1, 3))

            # Create timestamp (weighted toward past)
            years_ago = random.randint(1, 50)
            memory_timestamp = datetime.now() - timedelta(days=365 * years_ago)

            memories.append({
                'id': str(uuid.uuid4()),
                'title': title,
                'content': content,
                'imageUrl': image_url,
                'timestamp': memory_timestamp,
                'keywords': keywords,
                'metadata': {
                    'people': people,
                    'places': memory_places,
                    'topics': topics,
                    'type': memory_type
                }
            })

        # Store the memories
        db.collection('patientMemories').document(user_id).set(
            {'memories': memories})

    print(f"Generated memories for {len(user_ids)} users")
    return True


def generate_memory_vectors(user_ids):
    """Generate memory vectors based on patient memories, with proper subcollections for vector search"""
    print("Generating memory vectors from patient memories...")

    for user_id in user_ids:
        # Get patient memories
        memories_doc = db.collection('patientMemories').document(user_id).get()

        if not memories_doc.exists:
            continue

        memories = memories_doc.to_dict().get('memories', [])

        if not memories:
            continue

        # First create the patient document in patientMemoryVectors collection
        db.collection('patientMemoryVectors').document(user_id).set({
            'patientId':
            user_id,
            'totalMemories':
            len(memories),
            'lastUpdated':
            firestore.SERVER_TIMESTAMP
        })

        # Then get the chunks subcollection reference
        chunks_ref = db.collection('patientMemoryVectors').document(
            user_id).collection('chunks')

        # Process memories to create vector chunks
        for memory in memories:
            # For each memory, create a vector chunk
            summary = f"{memory.get('title', 'Untitled memory')}: {memory.get('content', '')[:200]}..."

            # Generate embedding vector
            vector = generate_real_embedding(summary)

            # Add document to chunks subcollection
            memory_id = memory.get('id', str(uuid.uuid4()))
            chunks_ref.document(memory_id).set({
                'id':
                memory_id,
                'summary':
                summary,
                'sourceId':
                memory_id,  # Reference to original memory
                'vector':
                vector,
                'keywords':
                memory.get('keywords', []),
                'timestamp':
                memory.get('timestamp', datetime.now()),
                'metadata':
                memory.get('metadata', {
                    'people': [],
                    'places': [],
                    'topics': [],
                    'type': 'unknown'
                })
            })

    print(f"Generated memory vectors for {len(user_ids)} users")


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


def test_vector_search(user_id, query_text="Tell me about my family"):
    """Test vector search functionality"""
    try:
        from google.cloud.firestore_v1 import VectorQuery

        print(
            f"Testing vector search for user {user_id} with query: '{query_text}'"
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
            user_id).collection("chunks")

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


def export_sample_ids(user_ids):
    """Export sample IDs to a JSON file for testing"""
    try:
        sample_data = {
            "users": user_ids,
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

    try:
        # Check if database already has data to avoid duplicate entries
        users_count = len(list(db.collection('users').limit(1).stream()))
        if users_count > 0:
            print(
                "Database already contains data. Aborting to prevent duplication."
            )
            print("If you want to repopulate, first clear the database.")
            return

        # Generate all data
        print("Starting database population...")
        user_ids = generate_sample_users(3)  # Generate 3 users
        generate_conversations(user_ids)
        generate_game_sessions(user_ids)
        generate_patient_memories(user_ids)
        generate_memory_vectors(user_ids)

        # Try to set up vector search indexes
        setup_vector_search()

        # Export sample IDs for testing
        export_sample_ids(user_ids)

        # Test vector search with a sample user
        if user_ids:
            test_vector_search(user_ids[0])

        end_time = time.time()
        print(
            f"Database populated successfully in {end_time - start_time:.2f} seconds!"
        )
        print("\nSample IDs for testing:")
        for i, user_id in enumerate(user_ids):
            print(f"User {i+1} ID: {user_id}")
        print(
            "\nNote: More sample IDs are available in the sample_ids.json file"
        )

    except Exception as e:
        print(f"Error during database population: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "populate":
        print("Starting database population...")
        populate_database()
    else:
        print("Usage: python populate_database.py populate")
