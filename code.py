
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

# Streamlit reruns the script whenever the user interacts
# with the page. Session state lets us remember information
# between those reruns.

if "messages" not in st.session_state:
    st.session_state.messages = []

if "feedback" not in st.session_state:
    st.session_state.feedback = None

if "original_audio" not in st.session_state:
    st.session_state.original_audio = None


# --------------------------------------------------
# Analyze a vocal recording
# --------------------------------------------------

def evaluate_vocal_take(
    audio_file_path: str,
    mime_type: str = None,
    performance_type: str = "Other",
    notes: str = ""
) -> str:

    """Uploads a vocal take to Gemini and analyzes it."""

    client = genai.Client()

    upload_config = (
        {"mime_type": mime_type}
        if mime_type
        else None
    )

    # --------------------------------------------------
    # Upload file to Gemini
    # --------------------------------------------------

    upload_start = time.time()

    with open(audio_file_path, "rb") as f:
        audio_file = client.files.upload(
            file=f,
            config=upload_config
        )

    print(
        f"Gemini file upload: "
        f"{time.time() - upload_start:.2f}s"
    )


    # --------------------------------------------------
    # Build context-aware prompt
    # --------------------------------------------------

    system_prompt = f"""
You are an experienced vocal producer and performance coach
who strongly values natural, expressive performances over
robotic pitch perfection.

The performer has identified this performance as:

{performance_type}

They have also made the following notes:
{notes}

Use this context when evaluating the performance.

If the performance is "Resinging the original", evaluate how well
the singer reproduces the intended character, emotion, phrasing,
and style of the original.

If it is "Cover / reinterpretation", do NOT assume the singer is
supposed to imitate the original artist. Evaluate their
interpretation on its own merits while considering whether their
choices effectively communicate the song.

If it is "My original song", focus primarily on the singer's own
artistic and technical choices.

If it is "Character performance / voice acting", evaluate whether
the vocal choices effectively communicate the intended character.
Do not criticize theatrical or exaggerated choices simply because
they are unconventional singing techniques.

If it is "Vocal experiment", focus on what the experiment is trying
to achieve and whether the chosen techniques accomplish that goal.

If it is "Other", use the available context and do not make
assumptions about the intended style.

IMPORTANT:

Do not treat an artistic preference as an objective technical flaw.

Separate observations into:

- Technical problems
- Intentional artistic choices
- Optional artistic suggestions

If the performer provides additional context later, reconsider
previous observations rather than automatically defending your
original assessment.

Listen closely to this audio clip.

Ignore minor pitch wanderings, small timing slips, or raw
imperfections unless they genuinely ruin the groove.

Evaluate the performance based primarily on:

1. Emotional Vulnerability

Does the artist sound like they mean it?
Where do they bleed, crack, or break open?

2. Character & Texture

How do they use grit, breath, fry, or dynamic strain to tell a story?

3. Risk-Taking

Did they lean into a risky, raw choice rather than playing it safe?

Give feedback like a veteran studio mentor who values soul and
humanity over mathematical perfection.

Do NOT focus solely on positives.

Do not dock the performer simply because they use an unconventional
technique if the technique works for the intended performance.

If something genuinely needs improvement, say so directly.

Stay as honest as possible.

Do not over compliment or over critique.

Only give credit where due and critique where needed.

For each section, separate:

- Compliments
- Critiques
- Neutral observations

Do not force any statements.

It is fine for one or more categories to be blank if there is
nothing genuine to say.

Do not invent things you cannot hear or determine from the recording such as the users exact pitch.

Always assume you could be wrong. Do not state certainties.
"""


    # --------------------------------------------------
    # Ask Gemini to analyze the recording
    # --------------------------------------------------

    analysis_start = time.time()

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=[
            audio_file,
            system_prompt
        ]
    )

    print(
        f"Gemini generation: "
        f"{time.time() - analysis_start:.2f}s"
    )


    # --------------------------------------------------
    # Keep the uploaded file available
    # for follow-up questions
    # --------------------------------------------------

    st.session_state.original_audio = audio_file.name

    # We intentionally DON'T delete the Gemini file here.
    #
    # Follow-up questions can reuse the same uploaded audio
    # instead of uploading it again.


    return response.text


# --------------------------------------------------
# Ask a follow-up question
# --------------------------------------------------

def ask_vocal_coach(
    question: str
) -> str:

    """Send a follow-up question using the existing conversation."""

    client = genai.Client()


    # --------------------------------------------------
    # Build conversation history
    # --------------------------------------------------

    conversation = ""

    for message in st.session_state.messages:

        conversation += (
            f"{message['role']}: "
            f"{message['content']}\n"
        )


    # --------------------------------------------------
    # Build follow-up prompt
    # --------------------------------------------------

    prompt = f"""
You are continuing a conversation as an experienced vocal producer
and performance coach.

The performer previously received an analysis of their vocal take.

Here is the conversation so far:

{conversation}

The user is now asking:

{question}

Answer the user's question directly.

Remember:

- The user is talking about the vocal performance you analyzed.
- Do not blindly agree with the user.
- Do not invent observations.
- Do not claim to hear something that you cannot determine.
- If your previous assessment was wrong or incomplete, acknowledge it.
- If the user provides new context, reconsider your earlier assessment.
- Distinguish technical problems from artistic choices.
- Do not treat your personal artistic preference as an objective rule.
- Give useful coaching rather than generic encouragement.
"""


    # --------------------------------------------------
    # Reuse original Gemini audio file
    # --------------------------------------------------

    contents = [prompt]

    if st.session_state.original_audio is not None:

        try:

            audio_file = client.files.get(
                name=st.session_state.original_audio
            )

            contents.append(audio_file)

        except Exception as e:

            print(
                f"Could not retrieve original audio: {e}"
            )


    # --------------------------------------------------
    # Generate follow-up response
    # --------------------------------------------------

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=contents
    )

    return response.text


# --------------------------------------------------
# Main page
# --------------------------------------------------

st.title("🎙️ AI Vocal Producer")

st.write(
    "Get feedback focused on emotional grit and humanity "
    "instead of robotic perfection."
)


# --------------------------------------------------
# Performance type
# --------------------------------------------------

performance_type = st.selectbox(
    "🎵 What kind of performance is this?",
    [
        "Resinging the original",
        "Cover / reinterpretation",
        "My original song",
        "Character performance / voice acting",
        "Vocal experiment",
        "Other"
    ]
)


# --------------------------------------------------
# Recording / Upload tabs
# --------------------------------------------------

tab_record, tab_upload = st.tabs(
    ["🎤 Record Take", "📁 Upload File"]
)

audio_to_process = None


# --------------------------------------------------
# Recording tab
# --------------------------------------------------

with tab_record:

    st.write(
        "Record a raw vocal snippet straight from your device microphone:"
    )

    notes = st.text_input("Do you have any notes, or specific questions?",
        key = "record_notes"
        )

    recorded_audio = st.audio_input(
        "Record your vocals"
    )

    if recorded_audio is not None:

        audio_to_process = recorded_audio


# --------------------------------------------------
# Upload tab
# --------------------------------------------------

with tab_upload:

    st.write(
        "Or choose an existing audio or video file from your device:"
    )

    notes = st.text_input("Do you have any notes, or specific questions?",
        key = "upload_notes"
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

            # --------------------------------------------------
            # Determine file extension
            # --------------------------------------------------

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


            # --------------------------------------------------
            # Get MIME type
            # --------------------------------------------------

            file_mime_type = getattr(
                audio_to_process,
                "type",
                None
            )


            # --------------------------------------------------
            # Save temporary local file
            # --------------------------------------------------

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


                # --------------------------------------------------
                # Analyze recording
                # --------------------------------------------------

                feedback = evaluate_vocal_take(
                    temp_path,
                    mime_type=file_mime_type,
                    performance_type=performance_type
                )


                # --------------------------------------------------
                # Save feedback
                # --------------------------------------------------

                st.session_state.feedback = feedback

                # Start a NEW conversation.
                #
                # The initial analysis is displayed separately,
                # so it should NOT be added to the chat history.

                st.session_state.messages = []


            except Exception as e:

                st.error(
                    f"An error occurred: {e}"
                )


            finally:

                # --------------------------------------------------
                # Delete local temporary file
                # --------------------------------------------------

                if os.path.exists(temp_path):

                    os.remove(temp_path)


# --------------------------------------------------
# Display producer feedback
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


    # --------------------------------------------------
    # Display conversation history
    # --------------------------------------------------

    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):

            st.write(
                message["content"]
            )


    # --------------------------------------------------
    # User follow-up
    # --------------------------------------------------

    user_message = st.chat_input(
        "Ask your vocal coach something..."
    )


    if user_message:

        # Display user's message

        with st.chat_message("user"):

            st.write(
                user_message
            )


        # Save user's message

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

