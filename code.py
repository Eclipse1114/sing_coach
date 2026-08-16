import os
import tempfile
import streamlit as st
from google import genai

# Page layout configuration
st.set_page_config(
    page_title="AI Vocal Producer", page_icon="🎙️", layout="centered"
)

# Initialize GenAI Client
client = genai.Client()

# System prompt defining the persona
SYSTEM_PROMPT = (
    "You are an experienced vocal producer and performance coach "
    "who deeply despises auto-tune, robotic pitch-perfection, and sterile, "
    "clinical vocal takes.\n\n"
    "Listen closely to the audio clips and follow-up text provided. Ignore minor pitch wanderings, "
    "small timing slips, or raw imperfections unless they genuinely ruin "
    "the groove. Instead, evaluate the performance and answer questions based entirely on:\n"
    "1. Emotional Vulnerability: Does the artist sound like they mean it? "
    "Where do they bleed, crack, or break open?\n"
    "2. Character & Texture: How do they use grit, breath, fry, or dynamic "
    "strain to tell a story?\n"
    "3. Risk-Taking: Did they lean into a risky, raw choice rather than "
    "playing it safe?\n\n"
    "Give feedback like a veteran studio mentor who values soul and humanity over mathematical perfection. "
    "Do NOT focus solely on positives, or dock them points because they have an unconventional technique, if it still sounds good. If something genuinely needs improvement, say so directly. "
    "Stay as honest as possible. Do not over compliment or over critique. Only give credit where due and critique where needed."
)

# Initialize chat session state for Gemini chat & UI history
if "chat_session" not in st.session_state:
    # Start a chat session with the system instruction configured
    st.session_state.chat_session = client.chats.create(
        model="gemini-2.5-flash",
        config={"system_instruction": SYSTEM_PROMPT}
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Streamlit UI Layout ---
st.title("🎙️ AI Vocal Producer")
st.write(
    "Get feedback focused on emotional grit and humanity instead of robotic "
    "perfection. Continue the session with follow-up takes or questions!"
)

# Display existing chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if "audio_bytes" in message and message["audio_bytes"]:
            st.audio(message["audio_bytes"])
        if "content" in message and message["content"]:
            st.markdown(message["content"])

# --- Input Section for New Turns ---
st.markdown("---")
st.subheader("Send a Follow-up Take or Message")

# Use tabs for input options (Recording vs Uploading)
tab_record, tab_upload = st.tabs(["🎤 Record Take", "📁 Upload File"])

audio_to_process = None

with tab_record:
    recorded_audio = st.audio_input("Record your vocals or reply", key="recorder_input")
    if recorded_audio is not None:
        audio_to_process = recorded_audio

with tab_upload:
    uploaded_file = st.file_uploader(
        "Choose an audio or video file", 
        type=["mp3", "wav", "m4a", "aac", "mp4", "mov", "avi"],
        key="uploader_input"
    )
    if uploaded_file is not None:
        audio_to_process = uploaded_file

# Text input for follow-up questions/notes
user_text = st.chat_input("Ask a question or add notes about your take...")

# Handle submission when either audio or text is provided
if st.button("Send to Producer", type="primary", use_container_width=True) or user_text or audio_to_process:
    if not user_text and not audio_to_process:
        st.warning("Please provide either an audio recording, uploaded file, or a text message.")
    else:
        # Prepare contents for Gemini API call
        gemini_contents = []
        audio_bytes_backup = None

        # Process audio if available
        if audio_to_process is not None:
            audio_bytes_backup = audio_to_process.getvalue()
            file_name = getattr(audio_to_process, "name", "recording.wav")
            suffix = os.path.splitext(file_name)[1]
            if not suffix:
                suffix = ".wav"
            file_mime_type = getattr(audio_to_process, "type", None)

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(audio_bytes_backup)
                temp_path = tmp.name

            try:
                upload_config = {"mime_type": file_mime_type} if file_mime_type else None
                with open(temp_path, "rb") as f:
                    uploaded_file_ref = client.files.upload(file=f, config=upload_config)
                gemini_contents.append(uploaded_file_ref)
            except Exception as e:
                st.error(f"Failed to upload audio: {e}")
                uploaded_file_ref = None
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        # Append text if available
        if user_text:
            gemini_contents.append(user_text)

        # Save user message to UI state
        st.session_state.messages.append({
            "role": "user",
            "content": user_text,
            "audio_bytes": audio_bytes_backup
        })

        with st.chat_message("user"):
            if audio_bytes_backup:
                st.audio(audio_bytes_backup)
            if user_text:
                st.markdown(user_text)

        # Generate response from the chat session
        with st.spinner("Producer is listening and reviewing..."):
            try:
                response = st.session_state.chat_session.send_message(gemini_contents)
                reply_text = response.text

                # Save assistant response to UI state
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply_text,
                    "audio_bytes": None
                })

                with st.chat_message("assistant"):
                    st.markdown(reply_text)

                # Clean up remote file reference if uploaded
                if audio_to_process is not None and 'uploaded_file_ref' in locals() and uploaded_file_ref:
                    client.files.delete(name=uploaded_file_ref.name)

                # Rererefresh to clear/reset widgets cleanly
                st.rerun()

            except Exception as e:
                st.error(f"An error occurred: {e}")
