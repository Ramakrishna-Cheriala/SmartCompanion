import logging
import speech_recognition as sr
import google.generativeai as genai
import win32com.client
import os
import tensorflow as tf
import webbrowser
import datetime
import subprocess
from dotenv import load_dotenv
from sklearn.svm import SVC
import nltk
import requests
import json
from tensorflow.keras.models import Sequential
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from tensorflow.keras.layers import Embedding, LSTM, Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.preprocessing.text import Tokenizer
from keras.utils import to_categorical
from tensorflow.keras.preprocessing.sequence import pad_sequences
import random
from dictonary import intents, country_names, generation_config, websites, apps_dict
from common_func import (
    speak,
    listen,
    remove_specific_words,
    remove_stop_words,
    get_location_from_query,
    detect_country_name,
    update_conversation_history,
)

import warnings

warnings.filterwarnings(
    "ignore", category=UserWarning, module="sklearn.feature_extraction.text"
)
warnings.filterwarnings("ignore", category=UserWarning, module="tensorflow")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
tf.get_logger().setLevel("ERROR")

load_dotenv()
api_key = os.getenv("OPEN_API_KEY")
weather_api_key = os.getenv("WEATHER_API_KEY")
news_api_key = os.getenv("NEWS_API_KEY")

log_file = "assistant_log.txt"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Set up a logger
logger = logging.getLogger(__name__)


def get_weather_details(location):
    weather_url = f"http://api.weatherapi.com/v1/current.json?key={weather_api_key}&q={location}&aqi=no"

    response = requests.get(weather_url).json()
    celsius = response["current"]["temp_c"]
    logger.info(f"The current temperature in {location} is {celsius} celsius")
    speak(f"The current temperature in {location} is {celsius} celsius")
    update_conversation_history(
        user_input,
        f"The current temperature in {location} is {celsius} celsius",
        conversation_history,
        conversation_history_file,
    )


def news_generator(query, country_names):
    country_code = detect_country_name(query, country_names)
    news_url = f"https://newsapi.org/v2/top-headlines?country={country_code}&apiKey={news_api_key}"
    response = requests.get(news_url).json()
    results_list = []

    for i in range(0, len(response["articles"])):
        print(
            "-----------------------------------------------------------------------------------------"
        )
        results = {}
        results["S.no"] = i
        print("\nTITLE:", response["articles"][i]["title"])
        results["title"] = response["articles"][i]["title"]
        print("\nPUBLISHED AT:", response["articles"][i]["publishedAt"])
        results["publishedAt"] = response["articles"][i]["publishedAt"]
        print("\nSOURCE LINK:", response["articles"][i]["url"])
        results["url"] = response["articles"][i]["url"]
        print("\nDESCRIPTION:", response["articles"][i]["description"])
        results["description"] = response["articles"][i]["description"]
        print("\nAUTHOR:", response["articles"][i]["author"])
        results["author"] = response["articles"][i]["author"]
        print(
            "-----------------------------------------------------------------------------------------"
        )
        results_list.append(results)  # Add the dictionary to the list

    update_conversation_history(
        user_input, results_list, conversation_history, conversation_history_file
    )


def ai_response(input):
    logger.info(f"User: {input}")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-pro", generation_config=generation_config
    )

    prompt_parts = [input]
    response = model.generate_content(prompt_parts)

    logger.info(f"AI Response: {response.text}")
    print(response.text)
    update_conversation_history(
        user_input, response.text, conversation_history, conversation_history_file
    )


def search_on_google(query):
    search_url = f"https://www.google.com/search?q={query}"
    webbrowser.open(search_url)
    logger.info(f"Searching on Google: {query}")


def search_on_youtube(query):
    search_url = f"https://www.youtube.com/results?search_query={query}"
    webbrowser.open(search_url)
    logger.info(f"Searching on YouTube: {query}")


def predict_intent(user_input, tokenizer, model, rnn_model):
    print("\npredict_intent started")
    input_vector = vect.transform([user_input])
    input_sequence = tokenizer.texts_to_sequences([user_input])
    input_padded = pad_sequences(
        input_sequence, maxlen=max_sequence_length, padding="post"
    )

    intent_svm = model.predict(input_vector)[0]

    intent_rnn_probabilities = rnn_model.predict(input_padded)
    intent_rnn_index = intent_rnn_probabilities.argmax(axis=-1)[0]
    intent_rnn = tokenizer.index_word[intent_rnn_index]

    if intent_rnn_probabilities[0][intent_rnn_index] > 0.5:
        intent = intent_rnn
    else:
        intent = intent_svm

    print(intent)
    print("\npredict_intent finished")
    return intent


def actions(user_input, intent):
    if intent == "open-website":
        for k, v in websites.items():
            if f"open {k}".lower() in user_input:
                speak(f"Opening {k}")
                webbrowser.open(v)
                logger.info(f"Opening {k}")
                break

    elif intent == "open-apps":
        for app_name, app_path in apps_dict.items():
            if f"open {app_name}".lower() in user_input:
                speak(f"Opening {app_name}")
                subprocess.Popen(app_path)
                logger.info(f"Opening {app_name} app")
                break

    elif intent == "time":
        current_time = datetime.datetime.now().strftime("%H:%M")
        speak(f"The current time is {current_time}")
        logger.info(f"The current time is {current_time}")
        update_conversation_history(
            intent,
            f"The current time is {current_time}",
            conversation_history,
            conversation_history_file,
        )

    elif intent == "search-google":
        specific_words_to_remove = ["google", "search"]
        query = remove_specific_words(user_input, specific_words_to_remove)
        query = remove_stop_words(query)
        search_on_google(query)

    elif intent == "search-youtube":
        specific_words_to_remove = ["youtube", "search"]
        query = remove_specific_words(user_input, specific_words_to_remove)
        query = remove_stop_words(query)
        search_on_youtube(query)

    elif intent == "weather":
        location = get_location_from_query(user_input)
        get_weather_details(location)

    elif intent == "news":
        news_generator(user_input, country_names)

    elif intent == "open-ai":
        ai_response(user_input)


conversation_history_file = "conversation_history.json"
try:
    with open(conversation_history_file, "r") as file:
        conversation_history = json.load(file)
except (FileNotFoundError, json.decoder.JSONDecodeError):
    conversation_history = []


training_data = []
labels = []

for k, v in intents.items():
    for pattern in v["patterns"]:
        training_data.append(pattern.lower())
        labels.append(k)

vect = TfidfVectorizer(
    tokenizer=nltk.word_tokenize, stop_words="english", max_df=0.8, min_df=1
)
X_train = vect.fit_transform(training_data)
X_train, X_test, Y_train, Y_test = train_test_split(
    X_train, labels, test_size=0.4, random_state=42, stratify=labels
)

model = SVC(kernel="linear", probability=True, C=1.0)
model.fit(X_train, Y_train)

# Tokenize and pad sequences for RNN model
tokenizer = Tokenizer()
tokenizer.fit_on_texts(training_data)
max_sequence_length = max(
    len(seq) for seq in tokenizer.texts_to_sequences(training_data)
)

rnn_model_file = "rnn_model.h5"
try:
    rnn_model = Sequential()
    rnn_model.add(Embedding(input_dim=len(tokenizer.word_index) + 1, output_dim=64))
    rnn_model.add(LSTM(128))
    rnn_model.add(Dense(len(intents), activation="softmax"))
    rnn_model.compile(
        loss="categorical_crossentropy", optimizer=Adam(), metrics=["accuracy"]
    )
    rnn_model.load_weights(rnn_model_file)

except (FileNotFoundError, OSError):
    rnn_model = Sequential()
    rnn_model.add(Embedding(input_dim=len(tokenizer.word_index) + 1, output_dim=64))
    rnn_model.add(LSTM(128))
    rnn_model.add(Dense(len(intents), activation="softmax"))
    rnn_model.compile(
        loss="categorical_crossentropy", optimizer=Adam(), metrics=["accuracy"]
    )

speak("Hello! How can I assist you?")
while True:
    try:
        n = int(input("Choose one option\n1. Voice\n2. Text\n\nEnter your choice: "))

        if n == 1:
            user_input = listen()
        elif n == 2:
            user_input = input("Enter your query: ")

        elif (
            user_input.lower() == "exit"
            or predict_intent(user_input, tokenizer, model, rnn_model) == "goodbye"
        ):
            speak("Goodbye!")
            break

        else:
            speak("Invalid input!")

        user_input = user_input.lower()

        intent = predict_intent(user_input, tokenizer, model, rnn_model)
        if intent in intents:
            responses = intents[intent]["responses"]
            response = random.choice(responses)
            # update_conversation_history(
            #     user_input, response, conversation_history, conversation_history_file
            # )
            speak(response)
            actions(user_input, intent)

        elif user_input.lower() == "history":
            for entry in conversation_history:
                print(f"User: {entry['user_input']}")
                print(f"AI: {entry['ai_response']}")

        else:
            speak("Sorry, I'm not sure how to respond to that.")

    except Exception as e:
        print(e)
        speak("An error occurred! Please try again")
