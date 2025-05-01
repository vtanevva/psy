from transformers import pipeline

emotion_classifier = pipeline("text-classification", model="bhadresh-savani/bert-base-uncased-emotion", top_k=1)

# keywords for suicide/self-harm detection - basic version
SUICIDE_KEYWORDS = ["kill myself", "end it all", "suicidal", "I want to die", "self-harm", "can't go on", "hurt myself"]

def detect_emotion(text):
    result = emotion_classifier(text)
    label = result[0][0]['label']
    score = result[0][0]['score']
    return label, score

def detect_suicidal_intent(text):
    lowered = text.lower()
    for keyword in SUICIDE_KEYWORDS:
        if keyword in lowered:
            return True
    return False
