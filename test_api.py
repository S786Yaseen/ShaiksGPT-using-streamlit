import google.generativeai as genai
import sys

API_KEY = "AIzaSyBui8aiNeq-evUGbcV1s0SSqtZjSZ4HpFs"
genai.configure(api_key=API_KEY)

try:
    models = genai.list_models()
    for m in models:
        print(m.name)
except Exception as e:
    print(f"Error: {e}")
