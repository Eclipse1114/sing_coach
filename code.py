import os
import tempfile
import streamlit as st
from google import genai

# Page layout configuration (using wide/centered layout cleanly for mobile screens)
st.set_page_config(
    page_title="AI Vocal Producer", page_icon="🎙️", layout="centered"
)


def evaluate_vocal_take(audio_file_path: str) -> str:
  """Uploads the track to Gemini and runs it against the anti-robot mentor prompt."""
  client = genai.Client()

  with open(audio_file_path, "rb") as f:
    audio_file = client.files.upload(file=f)

  system_prompt = (
      "You are an elite, counter-culture vocal producer and performance coach "
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
      "humanity over mathematical perfection."
  )

  response = client.models.generate_content(
      model="gemini-2.5-flash", contents=[audio_file, system_prompt]
  )

  # Clean up the file from Google's servers right after generating
  client.files.delete(name=audio_file.name)

  return response.text


# --- Streamlit UI Layout ---
st.title("🎙️ AI Vocal Producer")
st.write(
    "Get feedback focused on emotional grit and humanity instead of robotic "
    "perfection."
)

# Use tabs to provide a smooth mobile experience (Recording vs Uploading)
tab_record, tab_upload = st.tabs(["🎤 Record Take", "📁 Upload File"])

audio_to_process = None

with tab_record:
  st.write("Record a raw vocal snippet straight from your device microphone:")
  # Native mobile audio recording widget (supports iOS and Android browsers)
  recorded_audio = st.audio_input("Record your vocals")
  if recorded_audio is not None:
    audio_to_process = recorded_audio

with tab_upload:
  st.write("Or choose an existing audio file from your device:")
  uploaded_file = st.file_uploader(
      "Choose an audio file", type=["mp3", "wav", "m4a", "aac"]
  )
  if uploaded_file is not None:
    audio_to_process = uploaded_file

# Process whichever input source the user provided
if audio_to_process is not None:
  st.markdown("---")
  st.audio(audio_to_process)

  # Make primary buttons look big and easily tappable on touchscreens
  if st.button(
      "Run Producer Review", type="primary", use_container_width=True
  ):
    with st.spinner("Listening for soul and grit..."):
      # Determine file extension safely
      suffix = os.path.splitext(getattr(audio_to_process, "name", "recording.wav"))[
          1
      ]
      if not suffix:
        suffix = ".wav"

      with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_to_process.getvalue())
        temp_path = tmp.name

      try:
        feedback = evaluate_vocal_take(temp_path)
        st.markdown("---")
        st.subheader("Producer's Notes")
        st.write(feedback)
      except Exception as e:
        st.error(f"An error occurred: {e}")
      finally:
        # Clean up the local temp file
        if os.path.exists(temp_path):
          os.remove(temp_path)
