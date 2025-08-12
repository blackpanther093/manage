import pickle
from scipy.sparse import hstack
import os
import time

start_time = time.time()
# Assuming this file is in app/models/feedback_classifier.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load vectorizers and model once, on import
with open(os.path.join(BASE_DIR, "data", "word_vectorizer.pkl"), "rb") as f:
    word_vectorizer = pickle.load(f)

with open(os.path.join(BASE_DIR, "data", "char_vectorizer.pkl"), "rb") as f:
    char_vectorizer = pickle.load(f)

with open(os.path.join(BASE_DIR, "data", "classifier.pkl"), "rb") as f:
    model = pickle.load(f)

with open(os.path.join(BASE_DIR, "data", "label_encoder.pkl"), "rb") as f:
    label_encoder = pickle.load(f)

print(f"Feedback classifier loaded in {time.time() - start_time:.3f} seconds")

def classify_feedback(feedback_text):
    X_word = word_vectorizer.transform([feedback_text])
    X_char = char_vectorizer.transform([feedback_text])
    X = hstack([X_word, X_char])
    pred_numeric = model.predict(X)
    pred_label = label_encoder.inverse_transform(pred_numeric)[0]
    return pred_label

# test_feedbacks = [
#     "The milk had a weird chemical taste and I couldn’t drink it",
#     "Paratha was warm and crispy",
#     "Found a cockroach in the biryani",
#     "The dal was bland but edible",
#     "Curd was fresh and cool",
#     "Fish fry had a very foul smell",
#     "Chapati was soft and well-cooked",
#     "There was a nail in my food"
# ]

# classifications = [classify_feedback(feedback) for feedback in test_feedbacks]
# print("Classifications done in {:.3f} seconds".format(time.time() - start_time))
# for feedback, classification in zip(test_feedbacks, classifications):
    print(f"Feedback: {feedback}\nClassification: {classification}\n")