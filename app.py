import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api._errors import NoTranscriptFound
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import requests
url = 'https://ip.smartproxy.com/json'
username = 'spv47vc15k'
password = 'vntmSu4JjOAo1c+36v'
proxy = f"http://{username}:{password}@gate.smartproxy.com:7000"
proxies = {
    'http': proxy,
    'https': proxy,
}
response = requests.get(url, proxies=proxies)

st.write(response.text)

from youtube_transcript_api import YouTubeTranscriptApi
video_id = 'JFctWXEzFZw'
transcript = YouTubeTranscriptApi.get_transcript(video_id, proxies=proxies)
st.write(transcript)