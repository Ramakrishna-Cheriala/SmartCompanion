import logging
import speech_recognition as sr
import win32com.client
import os
import webbrowser
import datetime
import subprocess
from dotenv import load_dotenv
import google.generativeai as genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
import nltk
from dictonary import intents, websites, apps_dict, generation_config, country_names
import random
import re
from nltk.corpus import stopwords
import spacy
import requests

from common_func import (
    speak,
    remove_stop_words,
    get_location_from_query,
    detect_country_name,
    remove_specific_words,
    listen,
)

# nltk.download("punkt")
# nltk.download("stopwords")

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


def news_generator(query, country_names):
    country_code = detect_country_name(query, country_names)
    # print(country_code)
    news_url = f"https://newsapi.org/v2/top-headlines?country={country_code}&apiKey={news_api_key}"
    response = requests.get(news_url).json()
    # print(len(response["articles"]))
    for i in range(0, len(response["articles"])):
        print(
            "-----------------------------------------------------------------------------------------"
        )
        print("\nTITLE:", response["articles"][i]["title"])
        print("\nPUBLISHED AT:", response["articles"][i]["publishedAt"])
        print("\nSOURCE LINK:", response["articles"][i]["url"])
        print("\nDESCRIPTION:", response["articles"][i]["description"])
        print("\nAUTHOR:", response["articles"][i]["author"])
        print(
            "-----------------------------------------------------------------------------------------"
        )


def ai_response(input, context):
    logger.info(f"User: {input}")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-pro", generation_config=generation_config
    )

    prompt_parts = [context, input]
    response = model.generate_content(prompt_parts)

    logger.info(f"AI Response: {response.text}")
    print(response.text)


def search_on_google(query):
    search_url = f"https://www.google.com/search?q={query}"
    webbrowser.open(search_url)
    logger.info(f"Searching on Google: {query}")


def search_on_youtube(query):
    search_url = f"https://www.youtube.com/results?search_query={query}"
    webbrowser.open(search_url)
    logger.info(f"Searching on YouTube: {query}")


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

predictions = model.predict(X_test)


def predict_intent(user_input):
    user_input = user_input.lower()
    input_vector = vect.transform([user_input])
    intent = model.predict(input_vector)[0]
    print(intent)
    return intent


speak("Hello! How can I assist you?")
while True:
    try:
        n = int(input("Choose one option\n1. Voice\n2. Text\n\nEnter your choice: "))

        if n == 1:
            user_input = listen()
        elif n == 2:
            user_input = input("Enter your query: ")

        elif user_input.lower() == "exit" or predict_intent(user_input) == "goodbye":
            speak("Goodbye!")
            break

        else:
            speak("Invalid input!")

        intent = predict_intent(user_input)
        if intent in intents:
            responses = intents[intent]["responses"]
            response = random.choice(responses)
            speak(response)
            actions(user_input, intent)

        else:
            speak("Sorry, I'm not sure how to respond to that.")

    except Exception as e:
        speak("An error occurred! please try again")
