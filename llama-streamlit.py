import streamlit as st
import ollama
import speech_recognition as sr
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode, ClientSettings
from pydub import AudioSegment
from io import BytesIO
import av

# Custom audio processor to capture audio
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_buffer = BytesIO()

    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        audio = frame.to_ndarray()
        # Convert the audio numpy array to bytes
        audio_bytes = audio.tobytes()
        self.audio_buffer.write(audio_bytes)
        return frame

    def get_audio_buffer(self) -> BytesIO:
        return self.audio_buffer

# Speech recognition function
def recognize_speech_from_audio_buffer(audio_buffer: BytesIO):
    audio_buffer.seek(0)  # Reset buffer position to the beginning
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_buffer) as source:
        audio_data = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        return "Sorry, I could not understand the audio."
    except sr.RequestError as e:
        return f"Could not request results from Google Speech Recognition service; {e}"

def get_ai_response(messages):
    """Get AI response using Ollama."""
    try:
        response = ollama.chat(
            model='llama3.1',
            messages=messages
        )
        return response['message']['content']
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def main():
    st.title("Chat with Llama 3.1")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Audio recording
    st.subheader("Record your message:")

    # Initialize audio processor
    audio_processor = AudioProcessor()

    # WebRTC streamer for audio input
    webrtc_ctx = webrtc_streamer(
        key="audio",
        mode=WebRtcMode.SENDRECV,
        client_settings=ClientSettings(
            media_stream_constraints={
                "audio": True,
                "video": False,
            }
        ),
        audio_processor_factory=lambda: audio_processor,
        async_processing=False,
    )

    if webrtc_ctx.state.playing:
        st.write("Recording... Press 'Stop' when you're done.")

    if st.button("Stop Recording"):
        st.write("Stopped recording.")
        
        # Get the recorded audio buffer
        audio_buffer = audio_processor.get_audio_buffer()
        
        # Convert audio buffer to AudioSegment
        audio_buffer.seek(0)
        audio = AudioSegment.from_file(audio_buffer, format="raw", sample_width=2, frame_rate=48000, channels=1)
        
        # Save the audio to a temporary file
        temp_file = BytesIO()
        audio.export(temp_file, format="wav")
        
        # Recognize speech from the temporary audio file
        st.info("Processing audio...")
        prompt = recognize_speech_from_audio_buffer(temp_file)

        # Display recognized text
        st.markdown(f"**Recognized Text:** {prompt}")

        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        ai_response = get_ai_response(st.session_state.messages)

        # Display AI response
        if ai_response:
            with st.chat_message("assistant"):
                st.markdown(ai_response)

            # Add the AI response to chat history
            st.session_state.messages.append({"role": "assistant", "content": ai_response})

if __name__ == "__main__":
    main()
