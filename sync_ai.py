#!/usr/bin/env python3
# Ce script doit être exécuté avec le virtualenv du backend :
# backend/.venv/bin/python3 sync_ai.py
import os
import sys
import importlib.util

# Forcer l'utilisation du virtualenv du backend si exécuté avec le mauvais Python
venv_python = os.path.join(os.path.dirname(__file__), "backend", ".venv", "bin", "python3")
if sys.executable != venv_python and os.path.exists(venv_python):
    os.execv(venv_python, [venv_python] + sys.argv)

import google.generativeai as genai

# Ce script fusionne tout ton code et l'envoie à ton API Gemini
# pour faire un "Check-up" global avant de passer à l'étape suivante.

def generate_context():
    context = "### PROJECT STATE ###\n"
    with open("PROJECT_STATE.md", "r") as f:
        context += f.read() + "\n\n### CODEBASE ###\n"
    
    for root, dirs, files in os.walk("./src"): # Adapte le dossier
        for file in files:
            if file.endswith(('.py', '.js', '.ts', '.tsx')):
                with open(os.path.join(root, file), 'r') as f:
                    context += f"\n--- {file} ---\n" + f.read()
    return context

# Configure ton API Google AI Studio ici
genai.configure(api_key="AQ.Ab8RN6Jog9OT5da1qq-DqC3LifuDHiJ3T1Uzcrtz7W8JOO4nsw")
model = genai.GenerativeModel('gemini-1.5-pro')

print("Analyse de l'architecture en cours par Gemini Pro...")
response = model.generate_content(f"{generate_context()}\n\nIdentifie les bugs potentiels et propose une optimisation du code actuel.")
print(response.text)