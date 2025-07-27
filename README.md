# Namma Navigator - Bengaluru City Intelligence API

This project is an AI-powered API that monitors real-time city intelligence from social media (Reddit) and other sources to provide actionable insights about Bengaluru (Bangalore). It uses Google's Gemini API for analysis and Firebase for data storage.

## Project Setup

Follow these steps to get the project running.

### 1. Prerequisites

*   Python 3.9+
*   A Google Cloud Project with the **Gemini API** enabled.
*   A Firebase Project with a **Firestore Database**.
*   A Reddit App created to get API credentials.

### 2. Create Firebase Service Account Key

To allow the application to securely connect to your Firebase project, you need to create a service account key.

1.  Go to your [Firebase Project Settings](https://console.firebase.google.com/project/_/settings/serviceaccounts/adminsdk).
2.  Select your project.
3.  Click the **"Service accounts"** tab.
4.  Click the **"Generate new private key"** button. A JSON file will be downloaded.
5.  **Rename** this file to `firebase-service-account.json`.
6.  Place this file inside the `config/` directory in this project.

### 3. Create Environment File (`.env`)

The application requires API keys for Gemini and Reddit.

1.  Create a new file named `.env` inside the `config/` directory.
2.  Copy the following content into it and add your keys.

```env
# Get your API key from Google AI Studio: https://makersuite.google.com/app/apikey
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# Get your Reddit API credentials from: https://www.reddit.com/prefs/apps
REDDIT_CLIENT_ID="YOUR_REDDIT_CLIENT_ID"
REDDIT_CLIENT_SECRET="YOUR_REDDIT_CLIENT_SECRET"
REDDIT_USER_AGENT="NammaNavigator/1.0 by u/YourUsername"
```

### 4. Install Dependencies

Install all the required Python packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

---

## How to Run

### Run the API Server

To start the API server, run the `backendServer.py` script. The server will provide endpoints to fetch data and trigger analysis.

```bash
python src/backendServer.py
```
Once running, the API documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### Run the Test Scripts

To run a test cycle that fetches data from Reddit, processes it, and stores it in Firestore, use the `test_run.py` script.

```bash
python test_run.py
```
This will run a single, default test cycle to avoid exceeding API quotas on the free tier. You can edit the file to run more comprehensive tests.