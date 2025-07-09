/* global VAD */
const recipeEl = document.getElementById("recipe");
const startBtn = document.getElementById("start");
const transcriptEl = document.getElementById("transcript");

let ws;
let audioCtx, processor, vad;

startBtn.onclick = async () => {
  ws = new WebSocket(`ws://${location.host}/api/v1/ws`);

  ws.onopen = () => {
    ws.send(recipeEl.value);        // first frame = recipe text
    initMic();                      // then start audio
  };

  ws.onmessage = (evt) => {
    const data = JSON.parse(evt.data);
    if (data.delta) {
      transcriptEl.textContent += data.delta;
    }
    if (data.tts) {
      speechSynthesis.cancel();
      speechSynthesis.speak(new SpeechSynthesisUtterance(data.tts));
    }
  };
};

function initMic() {
  audioCtx = new AudioContext({ sampleRate: 48000 });
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const source = audioCtx.createMediaStreamSource(stream);
  processor = audioCtx.createScriptProcessor(4096, 1, 1);

  vad = VAD({ source, processor, onVoiceStart: () => {} });

  processor.onaudioprocess = (e) => {
    const float32 = e.inputBuffer.getChannelData(0);
    if (!vad.triggered) return;   // send only when speaking
    ws?.send(float32.buffer);
  };

  source.connect(processor);
  processor.connect(audioCtx.destination);
}
