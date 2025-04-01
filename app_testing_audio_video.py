import streamlit as st
import streamlit.components.v1 as components
import random

st.set_page_config(page_title="🎤📹 Customer Survey Recorder", layout="centered")

st.title("🧠 Customer Feedback Survey")
st.markdown("Record your responses as audio or video under each question!")

# Sample questions – customize these as needed
all_questions = [
    "What do you like most about our product?",
    "What do you wish we did better?",
    "How often do you use our service?",
    "Have you ever recommended us to someone?",
    "What made you choose us over competitors?",
    "How easy was it to get started?",
    "What features do you use the most?",
    "Have you ever had to contact support?",
    "How would you describe your overall experience?",
    "What would make you a lifelong customer?",
    "Is there something that almost made you not choose us?",
    "What's one thing you'd remove from the product?",
    "If you could wave a magic wand, what would you change?",
    "How likely are you to renew or repurchase?",
    "What do you use our product for, specifically?"
]

# Pick 10 random questions
questions = random.sample(all_questions, 10)

# Loop through each question and add audio + video recorders
for i, q in enumerate(questions, 1):
    st.subheader(f"{i}. {q}")

    # AUDIO recorder
    components.html(
        f"""
        <div>
          <strong>🎤 Record Audio Response:</strong><br>
          <button id="audioRecord{i}">🔴 Record</button>
          <button id="audioStop{i}" disabled>⏹ Stop</button><br>
          <audio id="audioPlayback{i}" controls></audio>
        </div>
        <script>
          let audioRecorder{i};
          let audioChunks{i} = [];

          document.getElementById("audioRecord{i}").onclick = async () => {{
            const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
            audioRecorder{i} = new MediaRecorder(stream);
            audioChunks{i} = [];

            audioRecorder{i}.ondataavailable = e => {{
              if (e.data.size > 0) audioChunks{i}.push(e.data);
            }};

            audioRecorder{i}.onstop = () => {{
              const blob = new Blob(audioChunks{i}, {{ type: 'audio/webm' }});
              document.getElementById("audioPlayback{i}").src = URL.createObjectURL(blob);
            }};

            audioRecorder{i}.start();
            document.getElementById("audioRecord{i}").disabled = true;
            document.getElementById("audioStop{i}").disabled = false;
          }};

          document.getElementById("audioStop{i}").onclick = () => {{
            audioRecorder{i}.stop();
            document.getElementById("audioRecord{i}").disabled = false;
            document.getElementById("audioStop{i}").disabled = true;
          }};
        </script>
        """,
        height=180,
    )

    # VIDEO recorder
    components.html(
        f"""
        <div>
          <strong>📹 Record Video Response:</strong><br>
          <video id="videoPreview{i}" width="320" height="240" autoplay muted></video><br>
          <button id="videoRecord{i}">🔴 Record</button>
          <button id="videoStop{i}" disabled>⏹ Stop</button><br>
          <video id="videoPlayback{i}" width="320" height="240" controls></video>
        </div>
        <script>
          let videoStream{i};
          let videoRecorder{i};
          let videoChunks{i} = [];

          const preview{i} = document.getElementById("videoPreview{i}");
          const playback{i} = document.getElementById("videoPlayback{i}");

          document.getElementById("videoRecord{i}").onclick = async () => {{
            videoStream{i} = await navigator.mediaDevices.getUserMedia({{ video: true, audio: true }});
            preview{i}.srcObject = videoStream{i};

            videoRecorder{i} = new MediaRecorder(videoStream{i});
            videoChunks{i} = [];

            videoRecorder{i}.ondataavailable = e => {{
              if (e.data.size > 0) videoChunks{i}.push(e.data);
            }};

            videoRecorder{i}.onstop = () => {{
              const blob = new Blob(videoChunks{i}, {{ type: 'video/webm' }});
              playback{i}.src = URL.createObjectURL(blob);
              videoStream{i}.getTracks().forEach(track => track.stop());
            }};

            videoRecorder{i}.start();
            document.getElementById("videoRecord{i}").disabled = true;
            document.getElementById("videoStop{i}").disabled = false;
          }};

          document.getElementById("videoStop{i}").onclick = () => {{
            videoRecorder{i}.stop();
            document.getElementById("videoRecord{i}").disabled = false;
            document.getElementById("videoStop{i}").disabled = true;
          }};
        </script>
        """,
        height=550,
    )

st.success("That's it! Your responses are saved locally in-browser for now. 🔒")

