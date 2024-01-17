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


speaker = win32com.client.Dispatch("SAPI.SpVoice")


def speak(text):
    print(f"AI: {text}")
    speaker.Speak(text)


def listen():
    # print("Recognizing...")
    r = sr.Recognizer()
    with sr.Microphone() as src:
        print("Listening.....")
        r.pause_threshold = 1
        audio = r.listen(src, 0, 8)
        try:
            voice_input = r.recognize_google(audio, language="en-in")
            print(f"User (Voice): {voice_input}")
            return voice_input.lower()
        except sr.UnknownValueError:
            speak("Sorry, I didn't catch that. Please try again.")
            return None
        except sr.RequestError as e:
            print(f"Google API request error: {e}")
            speak("Some error occurred. Please try again.")
            return None


def remove_stop_words(text):
    stop_words = set(stopwords.words("english"))
    stop_words.add("google")
    stop_words.add("search")
    stop_words.add("youtube")
    words = nltk.word_tokenize(text)
    filtered_words = [word for word in words if word.lower() not in stop_words]
    return " ".join(filtered_words)


def get_location_from_query(query):
    nlp = spacy.load("en_core_web_lg")
    doc = nlp(query)
    locations = [ent.text for ent in doc.ents if ent.label_ == "GPE"]
    return locations[0] if locations else None


def detect_country_name(query, country_names):
    detected_languages = []
    for word in query.split():
        if word.lower() in country_names:
            detected_languages.append(country_names[word.lower()])
    return detected_languages[0]


def remove_specific_words(text, specific_words):
    words = nltk.word_tokenize(text)
    filtered_words = [word for word in words if word.lower() not in specific_words]
    return " ".join(filtered_words)
