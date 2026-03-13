from translation_service import translate_to_telugu
try:
    print("Testing translation...")
    result = translate_to_telugu("Hello, how are you?")
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")
