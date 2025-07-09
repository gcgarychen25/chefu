/**
 * Simple Voice Activity Detection (VAD)
 * Detects when audio input exceeds a threshold
 */
function VAD({ source, processor, onVoiceStart, onVoiceEnd }) {
  let triggered = false;
  let silenceCount = 0;
  const SILENCE_THRESHOLD = 10; // frames of silence before stopping
  const VOLUME_THRESHOLD = 0.01; // minimum volume to consider as voice
  let isPaused = false; // Add pause state

  const vad = {
    triggered: false,
    
    process(audioData) {
      // Don't process if paused
      if (isPaused) {
        return;
      }
      
      // Calculate RMS (Root Mean Square) for volume detection
      let sum = 0;
      for (let i = 0; i < audioData.length; i++) {
        sum += audioData[i] * audioData[i];
      }
      const rms = Math.sqrt(sum / audioData.length);
      
      if (rms > VOLUME_THRESHOLD) {
        if (!this.triggered) {
          this.triggered = true;
          triggered = true;
          silenceCount = 0;
          if (onVoiceStart) onVoiceStart();
        }
      } else {
        silenceCount++;
        if (this.triggered && silenceCount > SILENCE_THRESHOLD) {
          this.triggered = false;
          triggered = false;
          silenceCount = 0;
          if (onVoiceEnd) onVoiceEnd();
        }
      }
    },
    
    pause() {
      console.log("⏸️ VAD paused");
      isPaused = true;
      // Reset triggered state when pausing
      if (this.triggered) {
        this.triggered = false;
        triggered = false;
        silenceCount = 0;
        if (onVoiceEnd) onVoiceEnd();
      }
    },
    
    resume() {
      console.log("▶️ VAD resumed");
      isPaused = false;
      silenceCount = 0; // Reset silence count when resuming
    },
    
    isPaused() {
      return isPaused;
    }
  };

  // Auto-process audio when available
  if (processor) {
    processor.onaudioprocess = (e) => {
      const audioData = e.inputBuffer.getChannelData(0);
      vad.process(audioData);
    };
  }

  return vad;
}

// Make VAD available globally
window.VAD = VAD;
