import os
import tempfile
import time

import streamlit as st
from google import genai


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="AI Vocal Producer",
    page_icon="🎙️",
    layout="centered"
)


# --------------------------------------------------
# Session state
# --------------------------------------------------

# Streamlit reruns this script whenever the user interacts
# with the page. Session state lets us remember information
# between those reruns.

if "messages" not in st.session_state:
    st.session_state.messages = []

if "feedback" not in st.session_state:
    st.session_state.feedback = None

if "original_audio" not in st.session_state:
    st.session_state.original_audio = None


# --------------------------------------------------
# Vocal coach prompt
# --------------------------------------------------

SYSTEM_PROMPT = (
    "You are an experienced vocal producer and performance coach "
    "who deeply despises auto-tune, robotic pitch-perfection, and sterile, "
    "clinical vocal takes.\n\n"

    "Listen closely to this audio clip. Ignore minor pitch wanderings, "
    "small timing slips, or raw imperfections unless they genuinely ruin "
    "the groove. Instead, evaluate the performance based entirely on:\n"

    "1. Emotional Vulnerability: Does the artist sound like they mean it? "
    "Where do they bleed, crack, or break open?\n"

    "2. Character & Texture: How do they use grit, breath, fry, or dynamic "
    "strain to tell a story?\n"

    "3. Risk-Taking: Did they lean into a risky, raw choice rather than "
    "playing it safe?\n\n"

    "Give feedback like a veteran studio mentor who values soul and "
    "humanity over mathematical perfection.\n"

    "Do NOT focus solely on positives, or dock them points because they "
    "have an unconventional technique if it still sounds good. "
    "If something genuinely needs improvement, say so directly.\n"

    "Stay as honest as possible. Do not over compliment or over critique. "
    "Only give credit where due and critique where needed.\n"

    "For each section, separate critiques, compliments, and neutral "
    "statements separately. Do not force any statements. "
    "It is fine to have one or two of these categories blank if there "
    "is nothing genuine to say.\n\n"

    "When answering follow-up questions, remember that the user is "
    "talking about the vocal performance you previously analyzed. "
    "Do not invent things you cannot hear or determine from the recording."
)


# --------------------------------------------------
# Analyze a vocal recording
# --------------------------------------------------

def evaluate_vocal_take(
    audio_file_path: str,
    mime_type: str = None
) -> str:

    """Uploads a vocal take to Gemini and analyzes it."""

    client = genai.Client()

    upload_config = (
        {"mime_type": mime_type}
        if mime_type
        else None
    )

    with open(audio_file_path, "rb") as f:
        audio_file = client.files.upload(
            file=f,
            config=upload_config
        )

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=[
            audio_file,
            SYSTEM_PROMPT
        ]
    )

    # Save the uploaded file's Gemini name so that we can
    # potentially reuse it during this session.
    st.session_state.original_audio = audio_file.name

    # IMPORTANT:
    # We are NOT deleting the Gemini file yet.
    #
    # The follow-up questions need access to the original audio.
    #
    # We will clean it up later when we add proper session
    # reset/cleanup functionality.

    return response.text


# --------------------------------------------------
# Ask a follow-up question
# --------------------------------------------------

def ask_vocal_coach(
    question: str
) -> str:

    """Send a follow-up question using the existing conversation."""

    client = genai.Client()

    # Build a readable version of the conversation.
    conversation = ""

    for message in st.session_state.messages:
        conversation += (
            f"{message['role']}: "
            f"{message['content']}\n"
        )

    prompt = f"""
{SYSTEM_PROMPT}

The following is the conversation that has happened so far:

{conversation}

The user is now asking:

{question}

Answer the user's question directly.

Remember:
- They are asking about the vocal performance you analyzed.
- Do not blindly agree with them.
- Do not invent observations.
- If you were wrong or uncertain about something earlier, say so.
- Give useful coaching rather than generic encouragement.
"""

    # If we have the original audio stored, retrieve it
    # so Gemini can use it when answering follow-ups.

    contents = [prompt]

    if st.session_state.original_audio is not None:

        try:
            audio_file = client.files.get(
                name=st.session_state.original_audio
            )

            contents.append(audio_file)

        except Exception as e:

            # If the original file is no longer available,
            # the AI can still answer from the conversation.
            print(
                f"Could not retrieve original audio: {e}"
            )

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=contents
    )

    return response.text


# --------------------------------------------------
# Page UI
# --------------------------------------------------

st.title("🎙️ AI Vocal Producer")

st.write(
    "Get feedback focused on emotional grit and humanity "
    "instead of robotic perfection."
)


# --------------------------------------------------
# Recording / Upload tabs
# --------------------------------------------------

tab_record, tab_upload = st.tabs(
    ["🎤 Record Take", "📁 Upload File"]
)

audio_to_process = None


# --------------------------------------------------
# Recording
# --------------------------------------------------

with tab_record:

    st.write(
        "Record a raw vocal snippet straight from your device microphone:"
    )

    recorded_audio = st.audio_input(
        "Record your vocals"
    )

    if recorded_audio is not None:
        audio_to_process = recorded_audio


# --------------------------------------------------
# Upload
# --------------------------------------------------

with tab_upload:

    st.write(
        "Or choose an existing audio or video file from your device:"
    )

    uploaded_file = st.file_uploader(
        "Choose an audio or video file",
        type=[
            "mp3",
            "wav",
            "m4a",
            "aac",
            "mp4",
            "mov",
            "avi"
        ],
        key="uploader_input"
    )

    if uploaded_file is not None:
        audio_to_process = uploaded_file


# --------------------------------------------------
# Process first vocal take
# --------------------------------------------------

if audio_to_process is not None:

    st.markdown("---")

    st.audio(audio_to_process)

    if st.button(
        "Run Producer Review",
        type="primary",
        use_container_width=True
    ):

        start_time = time.time()

        with st.spinner(
            "Listening for soul and grit..."
        ):

            # Determine file extension
            file_name = getattr(
                audio_to_process,
                "name",
                "recording.wav"
            )

            suffix = os.path.splitext(
                file_name
            )[1]

            if not suffix:
                suffix = ".wav"

            # Get MIME type
            file_mime_type = getattr(
                audio_to_process,
                "type",
                None
            )

            # Save locally temporarily
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix
            ) as tmp:

                tmp.write(
                    audio_to_process.getvalue()
                )

                temp_path = tmp.name

            try:

                print(
                    f"Preparing file: "
                    f"{time.time() - start_time:.2f}s"
                )

                analysis_start = time.time()

                feedback = evaluate_vocal_take(
                    temp_path,
                    mime_type=file_mime_type
                )

                print(
                    f"Gemini analysis: "
                    f"{time.time() - analysis_start:.2f}s"
                )

                # Save the initial feedback
                st.session_state.feedback = feedback

                # Start a new conversation
                st.session_state.messages = []

            except Exception as e:

                st.error(
                    f"An error occurred: {e}"
                )

            finally:

                if os.path.exists(temp_path):
                    os.remove(temp_path)


# --------------------------------------------------
# Display original feedback
# --------------------------------------------------

if st.session_state.feedback is not None:

    st.markdown("---")

    st.subheader(
        "🎙️ Producer's Notes"
    )

    st.write(
        st.session_state.feedback
    )


# --------------------------------------------------
# Follow-up conversation
# --------------------------------------------------

if st.session_state.feedback is not None:

    st.markdown("---")

    st.subheader(
        "💬 Talk to Your Vocal Coach"
    )

    # Display conversation history
    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):

            st.write(
                message["content"]
            )

    # Text input for follow-up questions
    user_message = st.chat_input(
        "Ask your vocal coach something..."
    )

    if user_message:

        # Display user's message immediately
        with st.chat_message("user"):

            st.write(
                user_message
            )

        # Save user message
        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_message
            }
        )

        # Generate AI response
        with st.chat_message("assistant"):

            with st.spinner(
                "Listening..."
            ):

                response = ask_vocal_coach(
                    user_message
                )

                st.write(
                    response
                )

        # Save AI response
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response
            }
        )
