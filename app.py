import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api._errors import NoTranscriptFound
import google.generativeai as genai
import os
from pocketbase import PocketBase
from dotenv import load_dotenv
load_dotenv()


client = PocketBase(os.getenv('POCKETBASE_URL'))
admin_data = client.admins.auth_with_password(os.getenv('POCKETBASE_ADMIN_EMAIL'), os.getenv('POCKETBASE_ADMIN_PASSWORD'))


# Load environment variables
proxies = {'https': os.getenv('SMARTPROXY')}
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Prompts
prompt = '''
    role: system
    content:
    You are a helpful assistant that formats YouTube transcripts into a readable format. The youtube transcripts may be auto-generated and simply a long string of text.
    Format the transcript into sentences and paragraphs.
    Add bold to the beginning of each paragraph.
    Return the youtube transcript in markdown format, without code blocks or other formatting.

    role: user
    content: Here is the transcript -
    {formatted_transcript}
'''

summary_prompt = '''
    role: system
    content:
    You are a helpful assistant that summarizes YouTube transcripts into a short summary.
    Summarize the youtube transcript in markdown format, without code blocks or other formatting. Use a mix of bullet points and short sentences.
    Return the summary in markdown format, without code blocks or other formatting.
    role: user
    content: Here is the transcript -
    {formatted_transcript}
'''

question_prompt = '''
    role: system
    content:
    You are a helpful assistant that answers questions about a YouTube transcript.
    Answer the question in markdown format, without code blocks or other formatting.
    If the answer to the question cannot be found directly in the transcript, tell the user that the transcript does not contain the answer. Do not use any of your other knowledge.
    Here is the transcript -
    {formatted_transcript}
    role: user
    content: My question is -
    {question}
'''

class Transcript:
    def __init__(self) -> None:
        self.url: str | None = None
        self.transcript: list | None = None
        self.full_transcript_list: list | None = None
        self.manually_created_transcripts: list | None = None
        self.generated_transcripts: list | None = None
        self.english_transcripts: list | None = None
        self.transcript_list: list | None = None
        self.formatted_transcript: str = '...transcript will appear here...'
        self.summary: str = '...summary will appear here...'
        self.video_id: str | None = None
    
    def strip_url(self, url: str) -> str:
        # given https://www.youtube.com/watch?v=JFctWXEzFZw, return JFctWXEzFZw
        # or given https://youtu.be/JFUvhtT2Nsc?si=KaWhSkBINTJWQWX9, return JFUvhtT2Nsc
        if 'youtube.com/watch?v=' in url:
            self.video_id = url.split('v=')[-1].split('&')[0]
        elif 'youtu.be/' in url:
            self.video_id = url.split('/')[-1].split('?')[0]
        else:
            self.video_id = None
        return self.video_id

    def list_transcripts(self, url: str) -> list:
        self.transcript_list = YouTubeTranscriptApi.list_transcripts(self.video_id, proxies=proxies)
        available_transcripts = []
        
        try:
            self.manually_created_transcripts = self.transcript_list.find_manually_created_transcript(['en'])
            available_transcripts.append(self.manually_created_transcripts)
        except NoTranscriptFound:
            st.error("No manually created transcript found")

        try:
            self.generated_transcripts = self.transcript_list.find_generated_transcript(['en'])
            available_transcripts.append(self.generated_transcripts)
        except NoTranscriptFound:
            st.error("No generated transcript found")

        return [transcript for transcript in available_transcripts if transcript is not None]

    def get_transcript(self, selected_language: str) -> any:
        for transcript in self.transcript_list:
            if transcript.language == selected_language:
                return transcript
        return None

    def format_transcript(self, transcript: list) -> str:
        formatter = TextFormatter()
        formatted_transcript = formatter.format_transcript(transcript)
        response = model.generate_content(prompt.format(formatted_transcript=formatted_transcript))
        return response.text
    
    def summarize_transcript(self, formatted_transcript: str) -> str:
        response = model.generate_content(summary_prompt.format(formatted_transcript=formatted_transcript))
        return response.text

    def ask_question(self, question: str) -> str:
        response = model.generate_content(
            question_prompt.format(
                formatted_transcript=self.formatted_transcript, 
                question=question
            )
        )
        return response.text

# check if transcript exists in pocketbase, return transcript and summary if it does
def check_transcript_exists(video_id: str) -> tuple[str, str]:
    transcript = client.collection('videos').get_first_list_item(f"video_id = '{video_id}'")
    if transcript:
        return transcript.transcript, transcript.summary
    return None, None

st.title('YouTube Transcriber')
st.write('Enter a YouTube URL to get a transcript and summary')

# Initialize session state
if 'transcript' not in st.session_state:
    st.session_state.transcript = Transcript()
if 'languages' not in st.session_state:
    st.session_state.languages = ['Waiting for transcript...']
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = 'Transcript'

# URL input
url = st.text_input('Enter YouTube URL...')

if st.button('Submit'):
    with st.spinner('Fetching transcript...'):
        try:
            video_id = st.session_state.transcript.strip_url(url)
            try:
                transcript, summary = check_transcript_exists(video_id)
                st.success('Existing transcript found in database!')
                st.session_state.transcript.formatted_transcript = transcript
                st.session_state.transcript.summary = summary
            except:
                available_transcripts = st.session_state.transcript.list_transcripts(url)
                st.session_state.languages = [t.language for t in available_transcripts]
                st.success('Transcript list fetched successfully!')
        except Exception as e:
            st.error(f'Error fetching transcript: {e}')

# Language selection
selected_language = st.selectbox(
    'Select Language',
    options=st.session_state.languages
)

if st.button('Get Transcript'):
    with st.spinner('Processing transcript...'):
        selected_transcript = st.session_state.transcript.get_transcript(selected_language)
        if selected_transcript:
            transcript_data = selected_transcript.fetch()
            st.session_state.transcript.formatted_transcript = st.session_state.transcript.format_transcript(transcript_data)
            st.session_state.transcript.summary = st.session_state.transcript.summarize_transcript(
                st.session_state.transcript.formatted_transcript
            )
            try:
                print('Saving transcript to database...')
                client.collection('videos').create({
                    'video_id': st.session_state.transcript.video_id,
                    'transcript': st.session_state.transcript.formatted_transcript,
                    'summary': st.session_state.transcript.summary
                })
                st.success('Transcript saved to database.')
            except Exception as e:
                st.error(f'Error saving transcript to database: {e}')

# Tabs
tab1, tab2, tab3 = st.tabs(['Transcript', 'Summary', 'Q&A'])

with tab1:
    if st.session_state.transcript.formatted_transcript != '...transcript will appear here...':
        st.markdown(st.session_state.transcript.formatted_transcript)

with tab2:
    if st.session_state.transcript.summary != '...summary will appear here...':
        st.markdown(st.session_state.transcript.summary)

with tab3:
    question = st.text_input('Ask a question about the transcript...')
    if st.button('Ask'):
        if st.session_state.transcript.formatted_transcript != '...transcript will appear here...':
            with st.spinner('Getting answer...'):
                answer = st.session_state.transcript.ask_question(question)
                st.markdown(answer)
        else:
            st.warning('Please fetch a transcript first!')