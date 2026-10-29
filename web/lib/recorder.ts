"use client";
// Hands-free utterance recorder for the in-browser (Sarvam) call.
// Sarvam STT accepts WAV/MP3/PCM only, not the WebM/Opus that browsers record, so every utterance is
// decoded and re-encoded here as 16 kHz mono WAV (Sarvam's best rate). Voice activity detection adapts to
// the room: it measures the background level first, then treats anything clearly louder as speech.

export type Level = (rms: number, speaking: boolean) => void;

export class Recorder {
  private stream!: MediaStream;
  private ctx!: AudioContext;
  private analyser!: AnalyserNode;
  private rec: MediaRecorder | null = null;
  private stopFlag = false;

  async open() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    this.ctx = new AudioContext();
    if (this.ctx.state === "suspended") await this.ctx.resume();
    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 2048;
    this.ctx.createMediaStreamSource(this.stream).connect(this.analyser);
  }

  close() {
    this.cancel();
    this.stream?.getTracks().forEach((t) => t.stop());
    this.ctx?.close().catch(() => {});
  }

  /** Stop the current utterance now (user pressed "done"). */
  finish() {
    if (this.rec?.state === "recording") this.rec.stop();
  }

  /** True if the last listen() was aborted by cancel() (vs. nobody speaking). */
  get cancelled() {
    return this.stopFlag;
  }

  /** Abort without sending. */
  cancel() {
    this.stopFlag = true;
    if (this.rec?.state === "recording") this.rec.stop();
  }

  /**
   * Record one utterance. Resolves with a WAV blob, or null if nobody spoke.
   * endSilenceMs: how long a pause ends the utterance; noSpeechMs: give up if silent this long.
   */
  listen(onLevel?: Level, { endSilenceMs = 1300, maxMs = 15000, noSpeechMs = 10000 } = {}): Promise<Blob | null> {
    this.stopFlag = false;
    const chunks: Blob[] = [];
    const type = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "";
    const rec = new MediaRecorder(this.stream, type ? { mimeType: type } : undefined);
    this.rec = rec;
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    const buf = new Float32Array(this.analyser.fftSize);
    const t0 = performance.now();
    let noise = 0.004;
    let calibrated = false;
    let spoke = false;
    let lastVoice = t0;

    return new Promise((resolve) => {
      rec.onstop = async () => {
        if (this.stopFlag || !spoke || !chunks.length) return resolve(null);
        try {
          resolve(await toWav16k(new Blob(chunks, { type: rec.mimeType }), this.ctx));
        } catch {
          resolve(null);
        }
      };
      rec.start(200);
      const tick = () => {
        if (rec.state !== "recording") return;
        this.analyser.getFloatTimeDomainData(buf);
        let s = 0;
        for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i];
        const rms = Math.sqrt(s / buf.length);
        const now = performance.now();
        if (!calibrated) {
          noise = Math.max(noise, rms); // first 350 ms: learn the room's background level
          if (now - t0 > 350) calibrated = true;
        }
        const threshold = Math.min(0.03, Math.max(0.008, noise * 2.5)); // cap: talking during calibration must not raise it past normal speech
        const speaking = calibrated && rms > threshold;
        if (speaking) {
          spoke = true;
          lastVoice = now;
        }
        onLevel?.(rms, speaking);
        if ((spoke && now - lastVoice > endSilenceMs) || now - t0 > maxMs || (!spoke && now - t0 > noSpeechMs)) {
          rec.stop();
          return;
        }
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  }
}

/** Any browser-decodable audio blob -> 16 kHz mono 16-bit PCM WAV. */
export async function toWav16k(blob: Blob, ctx: BaseAudioContext): Promise<Blob> {
  const decoded = await ctx.decodeAudioData(await blob.arrayBuffer());
  const rate = 16000;
  const off = new OfflineAudioContext(1, Math.ceil(decoded.duration * rate), rate);
  const src = off.createBufferSource();
  src.buffer = decoded;
  src.connect(off.destination);
  src.start();
  const pcm = (await off.startRendering()).getChannelData(0);
  const out = new DataView(new ArrayBuffer(44 + pcm.length * 2));
  const str = (o: number, s: string) => [...s].forEach((c, i) => out.setUint8(o + i, c.charCodeAt(0)));
  str(0, "RIFF");
  out.setUint32(4, 36 + pcm.length * 2, true);
  str(8, "WAVE");
  str(12, "fmt ");
  out.setUint32(16, 16, true);
  out.setUint16(20, 1, true); // PCM
  out.setUint16(22, 1, true); // mono
  out.setUint32(24, rate, true);
  out.setUint32(28, rate * 2, true);
  out.setUint16(32, 2, true);
  out.setUint16(34, 16, true);
  str(36, "data");
  out.setUint32(40, pcm.length * 2, true);
  for (let i = 0; i < pcm.length; i++) {
    const v = Math.max(-1, Math.min(1, pcm[i]));
    out.setInt16(44 + i * 2, v < 0 ? v * 0x8000 : v * 0x7fff, true);
  }
  return new Blob([out], { type: "audio/wav" });
}
