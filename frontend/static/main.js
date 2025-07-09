/* global VAD */
const recipeEl = document.getElementById("recipe");
const startBtn = document.getElementById("start");
const testTTSBtn = document.getElementById("testTTS");
const transcriptEl = document.getElementById("transcript");

let ws;
let audioCtx, processor, vad;
let isConnected = false;
let isSpeaking = false;
let isListening = false;

// Add debugging info
console.log("chefu - JavaScript loaded");
console.log("Elements found:", {
  recipe: !!recipeEl,
  start: !!startBtn, 
  testTTS: !!testTTSBtn,
  transcript: !!transcriptEl
});

function updateButtonState() {
  if (!isConnected) {
    startBtn.textContent = "Start Cooking";
    startBtn.disabled = false;
  } else if (isSpeaking) {
    startBtn.textContent = "Speaking... 🔊";
    startBtn.disabled = true;
  } else if (isListening) {
    startBtn.textContent = "Listening... 🎤";
    startBtn.disabled = false;
    startBtn.onclick = endSession;
  } else {
    startBtn.textContent = "Connecting...";
    startBtn.disabled = true;
  }
}

function endSession() {
  console.log("🛑 Ending cooking session");
  if (ws) {
    ws.close();
  }
  if (audioCtx) {
    audioCtx.close();
  }
  speechSynthesis.cancel();
  
  isConnected = false;
  isSpeaking = false;
  isListening = false;
  
  startBtn.onclick = startCooking;
  updateButtonState();
}

async function startCooking() {
  console.log("🚀 Start button clicked!");
  
  try {
    // Clear any previous transcript
    transcriptEl.textContent = "";
    
    // Check if we have a recipe
    if (!recipeEl.value.trim()) {
      console.warn("No recipe text provided");
      alert("Please paste a recipe first!");
      return;
    }
    
    console.log("Recipe text:", recipeEl.value.substring(0, 100) + "...");
    
    // Set connecting state
    isConnected = false;
    isSpeaking = false;
    isListening = false;
    updateButtonState();
    
    console.log("Creating WebSocket connection to:", `ws://${location.host}/api/v1/ws`);
    // Use main OpenAI endpoint for full functionality
    ws = new WebSocket(`ws://${location.host}/api/v1/ws`);
    console.log("🚀 Connecting to main OpenAI WebSocket endpoint");

    ws.onopen = async () => {
      console.log("✅ WebSocket connected successfully");
      isConnected = true;
      updateButtonState();
      
      transcriptEl.textContent = "Connected! Initializing microphone...\n";
      
      console.log("Sending recipe text to server...");
      ws.send(recipeEl.value);        // first frame = recipe text
      
      console.log("Initializing microphone...");
      await initMic();                // then start audio
      
      transcriptEl.textContent += "Microphone ready! Starting conversation...\n";
      
      console.log("Sending ready signal to start conversation...");
      ws.send("READY");               // signal that we're ready for conversation
      
      console.log("🎤 Voice interaction started!");
    };

    ws.onmessage = (evt) => {
      console.log("📨 Message received from server:", evt.data);
      const data = JSON.parse(evt.data);
      
      // Handle AI response text deltas
      if (data.delta) {
        console.log("📝 AI response delta:", data.delta);
        transcriptEl.textContent += data.delta;
      }
      
      // Handle user speech transcription
      if (data.transcription) {
        console.log("🎯 User transcription:", data.transcription);
        transcriptEl.textContent += `\n[You said: "${data.transcription}"]\n`;
      }
      
      // Handle processed user speech  
      if (data.user_speech) {
        console.log("🎯 User speech processed:", data.user_speech);
        transcriptEl.textContent += `\n[Processed: "${data.user_speech}"]\n`;
      }
      
      // Handle errors
      if (data.error) {
        console.error("❌ Server error:", data.error);
        transcriptEl.textContent += `\n[❌ Error: ${data.error}]\n`;
      }
      
      // Handle test mode confirmations (for debugging)
      if (data.type === "audio_received") {
        console.log("🎵 Audio confirmed received:", data);
        if (data.chunk_number % 10 === 0) {  // Only show every 10th to avoid spam
          transcriptEl.textContent += `\n[Audio chunk ${data.chunk_number} received]\n`;
        }
      }
      if (data.type === "recipe_received" || data.type === "ready_confirmed") {
        console.log("✅ Server confirmation:", data);
      }
      if (data.tts) {
        console.log("🔊 TTS message:", data.tts);
        isSpeaking = true;
        isListening = false;
        updateButtonState();
        
        // Add status message
        transcriptEl.textContent += "\n[chefu is speaking...]\n";
        transcriptEl.textContent += `chefu: ${data.tts}\n`;
        
        // Check if speech synthesis is available
        if (!window.speechSynthesis) {
          console.error("❌ Speech synthesis not supported");
          transcriptEl.textContent += "[❌ Speech synthesis not available in this browser]\n";
          isSpeaking = false;
          isListening = true;
          updateButtonState();
          transcriptEl.textContent += "\n[🎤 Listening for your response... Speak now!]\n";
          return;
        }
        
        console.log("🔊 Available voices:", speechSynthesis.getVoices().length);
        console.log("🔊 Speech synthesis state:", speechSynthesis.speaking, speechSynthesis.pending);
        
        // Temporarily disable VAD to prevent interference
        if (vad) {
          vad.pause();
          console.log("⏸️ VAD paused during TTS");
        }
        
        speechSynthesis.cancel();
        
        // Wait longer for cancel to complete and create utterance
        setTimeout(() => {
          const utterance = new SpeechSynthesisUtterance(data.tts);
          utterance.lang = 'en-US';
          utterance.rate = 0.9;
          utterance.pitch = 1.0;
          utterance.volume = 1.0;
          
          // Try to get an English voice
          const voices = speechSynthesis.getVoices();
          const englishVoice = voices.find(voice => voice.lang.startsWith('en-'));
          if (englishVoice) {
            utterance.voice = englishVoice;
            console.log("🗣️ Using voice:", englishVoice.name, englishVoice.lang);
          }
          
          utterance.onstart = () => {
            console.log("🔊 TTS actually started playing");
          };
          
          utterance.onend = () => {
            console.log("🔊 TTS finished - re-enabling VAD and switching to listening");
            isSpeaking = false;
            isListening = true;
            updateButtonState();
            
            // Re-enable VAD after TTS completes
            if (vad) {
              vad.resume();
              console.log("▶️ VAD resumed after TTS");
            }
            
            // Add listening status
            transcriptEl.textContent += "\n[🎤 Listening for your response... Speak now!]\n";
          };
          
          utterance.onerror = (event) => {
            console.error("❌ TTS error:", event);
            transcriptEl.textContent += `[❌ TTS error: ${event.error}]\n`;
            
            // Re-enable VAD even on error
            if (vad) {
              vad.resume();
              console.log("▶️ VAD resumed after TTS error");
            }
            
            isSpeaking = false;
            isListening = true;
            updateButtonState();
            transcriptEl.textContent += "\n[🎤 Listening for your response... Speak now!]\n";
            
            // For interrupted error, try again once
            if (event.error === 'interrupted') {
              console.log("🔄 TTS was interrupted, retrying in 1 second...");
              setTimeout(() => {
                if (!isSpeaking) {  // Only retry if we're not already speaking
                  console.log("🔄 Retrying TTS...");
                  speechSynthesis.speak(utterance);
                }
              }, 1000);
            }
          };
          
          console.log("🔊 Starting speech synthesis...");
          speechSynthesis.speak(utterance);
          
          // Shorter fallback timeout with VAD re-enable
          setTimeout(() => {
            if (isSpeaking) {
              console.warn("⚠️ TTS seems stuck, forcing listening mode");
              speechSynthesis.cancel();
              
              if (vad) {
                vad.resume();
                console.log("▶️ VAD resumed after timeout");
              }
              
              isSpeaking = false;
              isListening = true;
              updateButtonState();
              transcriptEl.textContent += "\n[⚠️ TTS timeout - switching to listening mode]\n";
              transcriptEl.textContent += "\n[🎤 Listening for your response... Speak now!]\n";
            }
          }, 15000); // Increased to 15 second timeout to allow longer messages
          
        }, 500); // Wait longer for cancel to complete
      }
    };

    ws.onclose = (event) => {
      console.log("❌ WebSocket disconnected:", event.code, event.reason);
      endSession();
    };

    ws.onerror = (error) => {
      console.error("💥 WebSocket error:", error);
      alert("Connection failed. Please make sure the server is running at http://localhost:8000");
      endSession();
    };

  } catch (error) {
    console.error("💥 Error starting cooking:", error);
    alert("Startup failed: " + error.message);
    endSession();
  }
}

startBtn.onclick = startCooking;

async function initMic() {
  try {
    console.log("🎤 Requesting microphone access...");
    
    // Check if we're in a secure context (required for getUserMedia)
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("Your browser doesn't support microphone access. Please use HTTPS or localhost.");
    }
    
    audioCtx = new AudioContext({ sampleRate: 48000 });
    console.log("🎵 AudioContext created, sample rate:", audioCtx.sampleRate);
    
    const stream = await navigator.mediaDevices.getUserMedia({ 
      audio: {
        sampleRate: 48000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true
      } 
    });
    
    console.log("✅ Microphone access granted, stream:", stream.getTracks()[0].getSettings());
    
    const source = audioCtx.createMediaStreamSource(stream);
    processor = audioCtx.createScriptProcessor(4096, 1, 1);
    console.log("🎛️ Audio nodes created");

    vad = VAD({ 
      source, 
      processor, 
      onVoiceStart: () => {
        console.log("🗣️ Voice detected - starting to send audio");
        if (isListening) {
          transcriptEl.textContent += "\n[🗣️ Voice detected, processing...]\n";
        }
      },
      onVoiceEnd: () => {
        console.log("🤫 Voice ended - stopping audio");
        if (isListening) {
          transcriptEl.textContent += "\n[Processing your request...]\n";
        }
      }
    });

    processor.onaudioprocess = (e) => {
      const float32 = e.inputBuffer.getChannelData(0);
      
      // Let VAD process the audio
      vad.process(float32);
      
      // Send audio only when voice is detected, WebSocket is open, AND we're in listening mode
      if (vad.triggered && ws && ws.readyState === WebSocket.OPEN && isListening && !isSpeaking) {
        console.log("📡 Sending audio chunk, size:", float32.buffer.byteLength);
        ws.send(float32.buffer);
      }
    };

    source.connect(processor);
    processor.connect(audioCtx.destination);
    
    console.log("🎤 Audio processing initialized successfully");
    
    // Resume AudioContext if it's suspended (Chrome requirement)
    if (audioCtx.state === 'suspended') {
      console.log("▶️ Resuming AudioContext...");
      await audioCtx.resume();
    }
    
  } catch (error) {
    console.error("💥 Microphone initialization failed:", error);
    if (error.name === 'NotAllowedError') {
      alert("Microphone permission is required for voice features. Please allow microphone access.");
    } else if (error.name === 'NotFoundError') {
      alert("No microphone found. Please make sure a microphone is connected.");
    } else {
      alert("Microphone initialization failed: " + error.message);
    }
    throw error;
  }
}

// Add page load debugging
document.addEventListener('DOMContentLoaded', () => {
  console.log("🚀 DOM loaded, chefu ready!");
  console.log("Current URL:", window.location.href);
  console.log("WebSocket URL will be:", `ws://${location.host}/api/v1/ws`);
  
  // Load voices and test TTS availability
  function loadVoices() {
    const voices = speechSynthesis.getVoices();
    console.log("🗣️ Available voices:", voices.length);
    if (voices.length > 0) {
      console.log("🗣️ Sample voices:", voices.slice(0, 3).map(v => `${v.name} (${v.lang})`));
    }
  }
  
  // Load voices when available
  loadVoices();
  speechSynthesis.addEventListener('voiceschanged', loadVoices);
  
  // Test TTS capability when user first interacts
  let ttsTestCompleted = false;
  
  function testTTS() {
    if (ttsTestCompleted) return;
    
    console.log("🧪 Testing TTS capability...");
    const testUtterance = new SpeechSynthesisUtterance("Testing");
    testUtterance.volume = 0; // Silent test
    testUtterance.onstart = () => {
      console.log("✅ TTS test successful");
      ttsTestCompleted = true;
    };
    testUtterance.onerror = (event) => {
      console.warn("⚠️ TTS test failed:", event.error);
    };
    speechSynthesis.speak(testUtterance);
    ttsTestCompleted = true;
  }
  
  // Test TTS on first user interaction
  ['click', 'keydown'].forEach(event => {
    document.addEventListener(event, testTTS, { once: true });
  });
});

// Test TTS functionality independently
testTTSBtn.onclick = () => {
  console.log("🧪 Testing TTS button clicked");
  
  if (!window.speechSynthesis) {
    alert("❌ Speech synthesis not supported in this browser");
    return;
  }
  
  const testMessage = "Hello! This is a test of the text-to-speech functionality. If you can hear this, audio is working correctly.";
  
  // Cancel any ongoing speech
  speechSynthesis.cancel();
  
  setTimeout(() => {
    const utterance = new SpeechSynthesisUtterance(testMessage);
    utterance.lang = 'en-US';
    utterance.rate = 0.9;
    utterance.volume = 1.0;
    
    // Try to get an English voice
    const voices = speechSynthesis.getVoices();
    const englishVoice = voices.find(voice => voice.lang.startsWith('en-'));
    if (englishVoice) {
      utterance.voice = englishVoice;
      console.log("🗣️ Using voice for test:", englishVoice.name);
    }
    
    utterance.onstart = () => {
      console.log("✅ Test TTS started successfully");
      testTTSBtn.textContent = "Playing... 🔊";
      testTTSBtn.disabled = true;
    };
    
    utterance.onend = () => {
      console.log("✅ Test TTS completed successfully");
      testTTSBtn.textContent = "Test Audio 🔊";
      testTTSBtn.disabled = false;
    };
    
    utterance.onerror = (event) => {
      console.error("❌ Test TTS error:", event);
      alert(`TTS Error: ${event.error}`);
      testTTSBtn.textContent = "Test Audio 🔊";
      testTTSBtn.disabled = false;
    };
    
    console.log("🔊 Starting test TTS...");
    speechSynthesis.speak(utterance);
  }, 100);
};
