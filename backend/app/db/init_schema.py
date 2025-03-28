from .firebase import db

def schema_exists():
    """
    Check if the schema has already been initialized by looking for
    the schema template document in the users collection.
    """
    schema_doc_id = "schema_template"
    doc_ref = db.collection('users').document(schema_doc_id)
    doc = doc_ref.get()
    return doc.exists

def initialize_schema():
    """
    Initialize Firestore schema for users, conversations, gameSessions, and patientMemoryVectors
    with the specified structure without adding any sample data.
    """
    # Check if schema is already initialized
    if schema_exists():
        print("Schema already initialized. Skipping initialization.")
        return
    
    print("Initializing Firestore schema...")
    
    # Create schema validation documents
    # These are empty documents that define the expected structure
    
    # 1. Users Collection Schema
    user_schema = {
        'username': '',
        'password': '',
        'displayName': '',
        'type': '',  # "patient" or "caregiver"
        'createdAt': None,  # Will be a timestamp
        'connections': {
            'patients': [],  # For caregivers: list of patient IDs they manage
            'caregivers': []  # For patients: list of caregiver IDs who manage them
        }
    }
    
    # 2. Conversations Collection Schema
    conversation_schema = {
        'messages': [
            {
                'id': '',
                'sender': '',  # "patient" or "ai"
                'content': '',
                'timestamp': None,  # Will be a timestamp
                'topics': []  # For report insights
            }
        ]
    }
    
    # 3. Game Sessions Collection Schema
    game_session_schema = {
        'sessions': [
            {
                'id': '',
                'gameId': '',
                'startedAt': None,  # Will be a timestamp
                'completedAt': None,  # Will be a timestamp
                'score': 0,
                'questionData': [
                    {
                        'questionId': '',
                        'questionText': '',
                        'memoryCategory': '',  # "shortTerm", "longTerm", "temporal", "spatial" etc.
                        'patientAnswer': '',
                        'correctAnswer': '',
                        'isCorrect': False,
                        'responseTimeSeconds': 0
                    }
                ]
            }
        ]
    }
    
    # 4. Patient Memory Vectors Collection Schema for RAG
    patient_memory_vectors_schema = {
        'chunks': [
            {
                'id': '',
                'summary': '',  # Condensed version for faster retrieval
                'sourceId': '',  # Reference to original content if needed in other database
                'vector': [],    # Will be replaced with actual vectors in real documents
                'keywords': [],  # Key terms for additional filtering
                'timestamp': None,  # Will be a timestamp
                'metadata': {
                    'people': [],  # People mentioned
                    'places': [],  # Places mentioned
                    'topics': [],  # Topics covered
                    'type': ''
                }
            }
        ]
    }
    
    # Using "schema_template" instead of "__schema__" since __schema__ is reserved
    schema_doc_id = "schema_template"
    
    # Create temporary schema documents
    try:
        # Users schema
        db.collection('users').document(schema_doc_id).set(user_schema)
        print("- Users collection schema initialized")
        
        # Conversations schema
        db.collection('conversations').document(schema_doc_id).set(conversation_schema)
        print("- Conversations collection schema initialized")
        
        # Game Sessions schema
        db.collection('gameSessions').document(schema_doc_id).set(game_session_schema)
        print("- Game Sessions collection schema initialized")
        
        # Patient Memory Vectors schema for RAG
        db.collection('patientMemoryVectors').document(schema_doc_id).set(patient_memory_vectors_schema)
        print("- Patient Memory Vectors collection for RAG initialized")
        
        print("\nSchema initialization complete!")
        print(f"\nNote: Schema documents with ID '{schema_doc_id}' have been created in each collection.")
        print("These documents serve as a reference for the expected structure.")
        print("You may choose to delete them once your application is set up.")
        print("\nNOTE: After adding actual vector data to patientMemoryVectors, you'll need to create")
        print("a vector index using gcloud to enable vector search functionality.")
        
    except Exception as e:
        print(f"Error initializing schema: {e}")

if __name__ == "__main__":
    initialize_schema()