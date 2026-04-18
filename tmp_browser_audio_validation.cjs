const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { chromium } = require('playwright');

const ROOT = 'C:/Users/Yang/Desktop/miro';
const URL = 'http://127.0.0.1:5173/docs/exploration/ui/hifi/miro-hifi-prototype.html';
const AUDIO_FILE = 'C:/Users/Yang/Desktop/miro/tmp_hello_can_you_hear_me_delayed.wav';
const OUT_LOG = 'C:/Users/Yang/Desktop/miro/backend/uvicorn_local_8101.out.log';
const ERR_LOG = 'C:/Users/Yang/Desktop/miro/backend/uvicorn_local_8101.err.log';
const DB_PATH = 'C:/Users/Yang/Desktop/miro/backend/smoke.db';
const PYTHON = 'C:/Users/Yang/Desktop/miro/backend/.venv/Scripts/python.exe';
const EMAIL = '593976339@qq.com';
const PASSWORD = 'a1b2c3d4';
const TMP_DIR = 'C:/Users/Yang/Desktop/miro/tmp';
const EXPORTED_WAV = `${TMP_DIR}/browser_capture_hello_full.wav`;
const TRIMMED_WAV = `${TMP_DIR}/browser_capture_hello_trimmed.wav`;
const EXPORTED_WAV_48K = `${TMP_DIR}/browser_capture_hello_full_48k.wav`;
const TRIMMED_WAV_48K = `${TMP_DIR}/browser_capture_hello_trimmed_48k.wav`;
const LEFT_WAV_48K = `${TMP_DIR}/browser_capture_left_full_48k.wav`;
const LEFT_TRIMMED_WAV_48K = `${TMP_DIR}/browser_capture_left_trimmed_48k.wav`;
const RIGHT_WAV_48K = `${TMP_DIR}/browser_capture_right_full_48k.wav`;
const RIGHT_TRIMMED_WAV_48K = `${TMP_DIR}/browser_capture_right_trimmed_48k.wav`;
const WS_EXPORTED_WAV = `${TMP_DIR}/browser_ws_sent_hello_full.wav`;
const WS_TRIMMED_WAV = `${TMP_DIR}/browser_ws_sent_hello_trimmed.wav`;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function parseMaybeJson(raw) {
  if (typeof raw !== 'string') return raw;
  try {
    const obj = JSON.parse(raw);
    if (obj && typeof obj === 'object' && obj.type === 'audio' && obj.data) {
      return { ...obj, data: `<base64 ${obj.data.length} chars>` };
    }
    return obj;
  } catch {
    return raw;
  }
}

function computeFloatStats(samples) {
  const n = samples.length || 0;
  if (!n) {
    return { frameCount: 0, samplesPerFrame: 0, rms: 0, peak: 0, min: 0, max: 0, zeroRatio: 1, nearZeroRatio: 1 };
  }
  let min = Infinity;
  let max = -Infinity;
  let peak = 0;
  let sumSq = 0;
  let zero = 0;
  let nearZero = 0;
  for (let i = 0; i < n; i += 1) {
    const v = samples[i] || 0;
    if (v === 0) zero += 1;
    if (Math.abs(v) < 1e-4) nearZero += 1;
    if (v < min) min = v;
    if (v > max) max = v;
    const abs = Math.abs(v);
    if (abs > peak) peak = abs;
    sumSq += v * v;
  }
  return {
    frameCount: 1,
    samplesPerFrame: n,
    rms: Math.sqrt(sumSq / n),
    peak,
    min,
    max,
    zeroRatio: zero / n,
    nearZeroRatio: nearZero / n
  };
}

function summarizeFloatFrames(frames) {
  if (!frames.length) {
    return {
      frameCount: 0,
      samplesPerFrame: 0,
      rmsAvg: 0,
      rmsMax: 0,
      peakMax: 0,
      minObserved: 0,
      maxObserved: 0,
      zeroRatioAvg: 1,
      nearZeroRatioAvg: 1,
      speechFrameCount: 0,
      speechFrames: []
    };
  }
  let samplesPerFrame = 0;
  let rmsSum = 0;
  let rmsMax = 0;
  let peakMax = 0;
  let minObserved = Infinity;
  let maxObserved = -Infinity;
  let zeroRatioSum = 0;
  let nearZeroRatioSum = 0;
  const speechFrames = [];
  for (const frame of frames) {
    samplesPerFrame = frame.length || samplesPerFrame;
    rmsSum += frame.rms || 0;
    rmsMax = Math.max(rmsMax, frame.rms || 0);
    peakMax = Math.max(peakMax, frame.peak || 0);
    minObserved = Math.min(minObserved, frame.min || 0);
    maxObserved = Math.max(maxObserved, frame.max || 0);
    zeroRatioSum += frame.zeroRatio || 0;
    nearZeroRatioSum += frame.nearZeroRatio || 0;
    if ((frame.rms || 0) >= 0.01 || (frame.peak || 0) >= 0.05) {
      if (speechFrames.length < 12) speechFrames.push(frame);
    }
  }
  return {
    frameCount: frames.length,
    samplesPerFrame,
    rmsAvg: rmsSum / frames.length,
    rmsMax,
    peakMax,
    minObserved,
    maxObserved,
    zeroRatioAvg: zeroRatioSum / frames.length,
    nearZeroRatioAvg: nearZeroRatioSum / frames.length,
    speechFrameCount: speechFrames.length,
    speechFrames
  };
}

function concatAudioFrames(wsDetails) {
  const ws = wsDetails?.[0];
  if (!ws) return { frameBuffers: [], merged: Buffer.alloc(0), endSegmentSeen: false };
  const frameBuffers = [];
  let endSegmentSeen = false;
  for (const frame of ws.framesAfterSpeech || []) {
    let parsed = frame.parsed;
    if (frame.dir === 'sent' && typeof frame.raw === 'string') {
      try {
        parsed = JSON.parse(frame.raw);
      } catch {
        parsed = frame.parsed;
      }
    }
    if (frame.dir === 'sent' && parsed && typeof parsed === 'object' && parsed.type === 'audio' && typeof parsed.data === 'string') {
      frameBuffers.push(Buffer.from(parsed.data, 'base64'));
      continue;
    }
    if (frame.dir === 'sent' && parsed && typeof parsed === 'object' && parsed.type === 'end_segment') {
      endSegmentSeen = true;
      break;
    }
  }
  return {
    frameBuffers,
    merged: Buffer.concat(frameBuffers),
    endSegmentSeen
  };
}

function computeInt16Stats(buffer) {
  const sampleCount = Math.floor(buffer.length / 2);
  if (!sampleCount) {
    return {
      byteLength: 0,
      sampleCount: 0,
      minInt16: 0,
      maxInt16: 0,
      zeroRatio: 1,
      nonZeroRatio: 0,
      clippedRatio: 0,
      samplePreview: []
    };
  }
  let minInt16 = 32767;
  let maxInt16 = -32768;
  let zeroCount = 0;
  let clippedCount = 0;
  const samplePreview = [];
  for (let i = 0; i < sampleCount; i += 1) {
    const value = buffer.readInt16LE(i * 2);
    if (value < minInt16) minInt16 = value;
    if (value > maxInt16) maxInt16 = value;
    if (value === 0) zeroCount += 1;
    if (value <= -32768 || value >= 32767) clippedCount += 1;
    if (samplePreview.length < 24) samplePreview.push(value);
  }
  return {
    byteLength: buffer.length,
    sampleCount,
    minInt16,
    maxInt16,
    zeroRatio: zeroCount / sampleCount,
    nonZeroRatio: 1 - zeroCount / sampleCount,
    clippedRatio: clippedCount / sampleCount,
    samplePreview
  };
}

function frameRmsInt16(buffer) {
  const sampleCount = Math.floor(buffer.length / 2);
  if (!sampleCount) return 0;
  let sumSq = 0;
  for (let i = 0; i < sampleCount; i += 1) {
    const v = buffer.readInt16LE(i * 2) / 32768;
    sumSq += v * v;
  }
  return Math.sqrt(sumSq / sampleCount);
}

function trimSpeechBuffers(frameBuffers) {
  if (!frameBuffers.length) return Buffer.alloc(0);
  const rmsValues = frameBuffers.map((buf) => frameRmsInt16(buf));
  let first = rmsValues.findIndex((v) => v >= 0.01);
  if (first < 0) first = 0;
  let last = -1;
  for (let i = rmsValues.length - 1; i >= 0; i -= 1) {
    if (rmsValues[i] >= 0.01) {
      last = i;
      break;
    }
  }
  if (last < first) last = frameBuffers.length - 1;
  return Buffer.concat(frameBuffers.slice(first, last + 1));
}

function concatObservedInt16Frames(audioDiag, cutoffTs) {
  const frames = (audioDiag?.int16Frames || [])
    .filter((frame) => Number(frame.ts || 0) > cutoffTs)
    .map((frame) => Buffer.from(frame.base64 || '', 'base64'))
    .filter((buf) => buf.length > 0);
  return {
    frameBuffers: frames,
    merged: Buffer.concat(frames)
  };
}

function concatObservedPcm48Frames(audioDiag, cutoffTs) {
  const frames = (audioDiag?.pcm48Frames || [])
    .filter((frame) => Number(frame.ts || 0) > cutoffTs)
    .map((frame) => Buffer.from(frame.base64 || '', 'base64'))
    .filter((buf) => buf.length > 0);
  return {
    frameBuffers: frames,
    merged: Buffer.concat(frames)
  };
}

function concatObservedNamedFrames(audioDiag, key, cutoffTs) {
  const frames = (audioDiag?.[key] || [])
    .filter((frame) => Number(frame.ts || 0) > cutoffTs)
    .map((frame) => Buffer.from(frame.base64 || '', 'base64'))
    .filter((buf) => buf.length > 0);
  return {
    frameBuffers: frames,
    merged: Buffer.concat(frames)
  };
}

function writePcm16MonoWav(filePath, pcmBuffer, sampleRate = 16000) {
  const byteRate = sampleRate * 2;
  const blockAlign = 2;
  const dataSize = pcmBuffer.length;
  const header = Buffer.alloc(44);
  header.write('RIFF', 0);
  header.writeUInt32LE(36 + dataSize, 4);
  header.write('WAVE', 8);
  header.write('fmt ', 12);
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);
  header.writeUInt16LE(1, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(byteRate, 28);
  header.writeUInt16LE(blockAlign, 32);
  header.writeUInt16LE(16, 34);
  header.write('data', 36);
  header.writeUInt32LE(dataSize, 40);
  fs.writeFileSync(filePath, Buffer.concat([header, pcmBuffer]));
}

(async () => {
  ensureDir(TMP_DIR);
  const consoleEntries = [];
  const pageErrors = [];
  const webSockets = [];

  const browser = await chromium.launch({
    headless: false,
    args: [
      '--use-fake-device-for-media-stream',
      '--use-fake-ui-for-media-stream',
      '--autoplay-policy=no-user-gesture-required',
      `--use-file-for-fake-audio-capture=${AUDIO_FILE}`
    ]
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await context.grantPermissions(['microphone', 'camera'], { origin: 'http://127.0.0.1:5173' });
  const page = await context.newPage();

  page.on('console', (msg) => consoleEntries.push({ ts: Date.now(), type: msg.type(), text: msg.text() }));
  page.on('pageerror', (err) => pageErrors.push({ ts: Date.now(), text: err.message || String(err) }));
  page.on('websocket', (ws) => {
    if (!ws.url().includes('/voice')) return;
    const rec = { url: ws.url(), createdAt: Date.now(), frames: [], errors: [], closedAt: null };
    webSockets.push(rec);
    ws.on('framesent', (evt) => rec.frames.push({ dir: 'sent', ts: Date.now(), raw: evt.payload, parsed: parseMaybeJson(evt.payload) }));
    ws.on('framereceived', (evt) => rec.frames.push({ dir: 'recv', ts: Date.now(), raw: evt.payload, parsed: parseMaybeJson(evt.payload) }));
    ws.on('socketerror', (err) => rec.errors.push({ ts: Date.now(), text: String(err) }));
    ws.on('close', () => { rec.closedAt = Date.now(); });
  });

  await page.addInitScript(() => {
    const BaseAudioContextCtor = window.AudioContext || window.webkitAudioContext;
    if (BaseAudioContextCtor && !BaseAudioContextCtor.prototype.__codexPlaybackProbeInstalled) {
      const originalCreateBufferSource = BaseAudioContextCtor.prototype.createBufferSource;
      BaseAudioContextCtor.prototype.createBufferSource = function patchedCreateBufferSource(...args) {
        const source = originalCreateBufferSource.apply(this, args);
        if (source && typeof source.start === 'function' && !source.__codexPlaybackProbeWrapped) {
          const originalStart = source.start.bind(source);
          source.start = (...startArgs) => {
            try {
              window.__audioDiag = window.__audioDiag || { audioPlaybackStarts: [] };
              window.__audioDiag.audioPlaybackStarts = window.__audioDiag.audioPlaybackStarts || [];
              window.__audioDiag.audioPlaybackStarts.push({
                ts: Date.now(),
                when: Number(startArgs?.[0] || 0),
                hasBuffer: Boolean(source.buffer),
                sampleRate: Number(source.buffer?.sampleRate || 0),
                duration: Number(source.buffer?.duration || 0)
              });
            } catch (_) {}
            return originalStart(...startArgs);
          };
          source.__codexPlaybackProbeWrapped = true;
        }
        return source;
      };
      BaseAudioContextCtor.prototype.__codexPlaybackProbeInstalled = true;
    }

    const calcStats = (samples) => {
      const n = samples?.length || 0;
      if (!n) return { length: 0, rms: 0, peak: 0, min: 0, max: 0, zeroRatio: 1, nearZeroRatio: 1, preview: [] };
      let min = Infinity;
      let max = -Infinity;
      let peak = 0;
      let sumSq = 0;
      let zero = 0;
      let nearZero = 0;
      for (let i = 0; i < n; i += 1) {
        const v = samples[i] || 0;
        if (v === 0) zero += 1;
        if (Math.abs(v) < 1e-4) nearZero += 1;
        if (v < min) min = v;
        if (v > max) max = v;
        const abs = Math.abs(v);
        if (abs > peak) peak = abs;
        sumSq += v * v;
      }
      return {
        length: n,
        rms: Math.sqrt(sumSq / n),
        peak,
        min,
        max,
        zeroRatio: zero / n,
        nearZeroRatio: nearZero / n,
        preview: Array.from(samples.slice(0, 12))
      };
    };

    window.__audioDiag = {
      trackSettings: [],
      constraints: [],
      contexts: [],
      processors: [],
      floatFrames: [],
      int16Frames: [],
      pcm48Frames: [],
      leftPcm48Frames: [],
      rightPcm48Frames: [],
      audioPlaybackStarts: []
    };

    const mixToMono = (channels) => {
      if (!channels?.length) return new Float32Array(0);
      if (channels.length === 1) return channels[0];
      const length = channels[0].length || 0;
      const mixed = new Float32Array(length);
      for (let i = 0; i < length; i += 1) {
        let sum = 0;
        for (let c = 0; c < channels.length; c += 1) {
          sum += channels[c][i] || 0;
        }
        mixed[i] = sum / channels.length;
      }
      return mixed;
    };

    const resampleFloat32ToPcm16 = (input, inputSampleRate, targetSampleRate = 16000) => {
      if (!input || !input.length) return new Int16Array(0);
      if (inputSampleRate === targetSampleRate) {
        const out = new Int16Array(input.length);
        for (let i = 0; i < input.length; i += 1) {
          const s = Math.max(-1, Math.min(1, input[i]));
          out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        return out;
      }
      const ratio = inputSampleRate / targetSampleRate;
      const outLen = Math.floor(input.length / ratio);
      const out = new Int16Array(outLen);
      for (let i = 0; i < outLen; i += 1) {
        const srcIdx = i * ratio;
        const i0 = Math.floor(srcIdx);
        const i1 = Math.min(input.length - 1, i0 + 1);
        const t = srcIdx - i0;
        const sample = input[i0] * (1 - t) + input[i1] * t;
        const clipped = Math.max(-1, Math.min(1, sample));
        out[i] = clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff;
      }
      return out;
    };

    const int16Stats = (pcm16) => {
      const n = pcm16?.length || 0;
      if (!n) return { byteLength: 0, sampleCount: 0, minInt16: 0, maxInt16: 0, zeroRatio: 1, nonZeroRatio: 0, clippedRatio: 0, preview: [] };
      let minInt16 = 32767;
      let maxInt16 = -32768;
      let zero = 0;
      let clipped = 0;
      const preview = [];
      for (let i = 0; i < n; i += 1) {
        const value = pcm16[i];
        if (value < minInt16) minInt16 = value;
        if (value > maxInt16) maxInt16 = value;
        if (value === 0) zero += 1;
        if (value <= -32768 || value >= 32767) clipped += 1;
        if (preview.length < 24) preview.push(value);
      }
      return {
        byteLength: n * 2,
        sampleCount: n,
        minInt16,
        maxInt16,
        zeroRatio: zero / n,
        nonZeroRatio: 1 - zero / n,
        clippedRatio: clipped / n,
        preview
      };
    };

    const float32ToPcm16 = (input) => {
      if (!input || !input.length) return new Int16Array(0);
      const out = new Int16Array(input.length);
      for (let i = 0; i < input.length; i += 1) {
        const s = Math.max(-1, Math.min(1, input[i]));
        out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      return out;
    };

    const installObserver = async (stream) => {
      try {
        const track = stream.getAudioTracks?.()[0];
        if (!track) return stream;
        const cloned = track.clone();
        const observeStream = new MediaStream([cloned]);
        const Ctor = window.AudioContext || window.webkitAudioContext;
        if (!Ctor) return stream;
        const ctx = new Ctor();
        if (ctx.state === 'suspended') {
          try { await ctx.resume(); } catch (_) {}
        }
        const source = ctx.createMediaStreamSource(observeStream);
        const processor = ctx.createScriptProcessor(4096, 2, 1);
        window.__audioDiag.contexts.push({
          ctor: Ctor.name || 'AudioContext',
          sampleRate: ctx.sampleRate,
          state: ctx.state
        });
        window.__audioDiag.processors.push({
          bufferSize: processor.bufferSize || 4096,
          inputChannels: 2,
          outputChannels: 1,
          sampleRate: ctx.sampleRate
        });
        processor.onaudioprocess = (event) => {
          try {
            const channels = [];
            for (let i = 0; i < event.inputBuffer.numberOfChannels; i += 1) {
              channels.push(event.inputBuffer.getChannelData(i));
            }
            const mono = mixToMono(channels);
            const left = channels[0] || mono;
            const right = channels[1] || channels[0] || mono;
            const channelStats = channels.map((channel, index) => ({
              index,
              ...calcStats(channel)
            }));
            const stats = calcStats(mono);
            const leftPcm48 = float32ToPcm16(left);
            const rightPcm48 = float32ToPcm16(right);
            const pcm48 = float32ToPcm16(mono);
            const pcm16 = resampleFloat32ToPcm16(mono, event.inputBuffer.sampleRate, 16000);
            const leftPcm48Stats = int16Stats(leftPcm48);
            const rightPcm48Stats = int16Stats(rightPcm48);
            const pcm48Stats = int16Stats(pcm48);
            const pcmStats = int16Stats(pcm16);
            window.__audioDiag.floatFrames.push({
              ts: Date.now(),
              sampleRate: event.inputBuffer.sampleRate,
              channelCount: event.inputBuffer.numberOfChannels,
              channelStats,
              ...stats
            });
            const bytes = new Uint8Array(pcm16.buffer, pcm16.byteOffset, pcm16.byteLength);
            let binary = '';
            const chunkSize = 0x8000;
            for (let i = 0; i < bytes.length; i += chunkSize) {
              binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
            }
            const bytes48 = new Uint8Array(pcm48.buffer, pcm48.byteOffset, pcm48.byteLength);
            let binary48 = '';
            for (let i = 0; i < bytes48.length; i += chunkSize) {
              binary48 += String.fromCharCode.apply(null, bytes48.subarray(i, i + chunkSize));
            }
            const leftBytes48 = new Uint8Array(leftPcm48.buffer, leftPcm48.byteOffset, leftPcm48.byteLength);
            let leftBinary48 = '';
            for (let i = 0; i < leftBytes48.length; i += chunkSize) {
              leftBinary48 += String.fromCharCode.apply(null, leftBytes48.subarray(i, i + chunkSize));
            }
            const rightBytes48 = new Uint8Array(rightPcm48.buffer, rightPcm48.byteOffset, rightPcm48.byteLength);
            let rightBinary48 = '';
            for (let i = 0; i < rightBytes48.length; i += chunkSize) {
              rightBinary48 += String.fromCharCode.apply(null, rightBytes48.subarray(i, i + chunkSize));
            }
            window.__audioDiag.pcm48Frames.push({
              ts: Date.now(),
              sampleRate: event.inputBuffer.sampleRate,
              ...pcm48Stats,
              base64: btoa(binary48)
            });
            window.__audioDiag.leftPcm48Frames.push({
              ts: Date.now(),
              sampleRate: event.inputBuffer.sampleRate,
              ...leftPcm48Stats,
              base64: btoa(leftBinary48)
            });
            window.__audioDiag.rightPcm48Frames.push({
              ts: Date.now(),
              sampleRate: event.inputBuffer.sampleRate,
              ...rightPcm48Stats,
              base64: btoa(rightBinary48)
            });
            window.__audioDiag.int16Frames.push({
              ts: Date.now(),
              sampleRate: 16000,
              ...pcmStats,
              base64: btoa(binary)
            });
            if (window.__audioDiag.floatFrames.length > 1200) {
              window.__audioDiag.floatFrames.splice(0, window.__audioDiag.floatFrames.length - 1200);
            }
            if (window.__audioDiag.int16Frames.length > 1200) {
              window.__audioDiag.int16Frames.splice(0, window.__audioDiag.int16Frames.length - 1200);
            }
            if (window.__audioDiag.pcm48Frames.length > 1200) {
              window.__audioDiag.pcm48Frames.splice(0, window.__audioDiag.pcm48Frames.length - 1200);
            }
            if (window.__audioDiag.leftPcm48Frames.length > 1200) {
              window.__audioDiag.leftPcm48Frames.splice(0, window.__audioDiag.leftPcm48Frames.length - 1200);
            }
            if (window.__audioDiag.rightPcm48Frames.length > 1200) {
              window.__audioDiag.rightPcm48Frames.splice(0, window.__audioDiag.rightPcm48Frames.length - 1200);
            }
          } catch (_) {}
        };
        source.connect(processor);
        processor.connect(ctx.destination);
      } catch (_) {}
      return stream;
    };

    const RAW_AUDIO_CONSTRAINTS = {
      channelCount: 1,
      sampleRate: 16000,
      sampleSize: 16,
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false
    };

    const originalGetUserMedia = navigator.mediaDevices?.getUserMedia?.bind(navigator.mediaDevices);
    if (originalGetUserMedia) {
      navigator.mediaDevices.getUserMedia = async function wrappedGetUserMedia(constraints) {
        const effectiveConstraints = (constraints && typeof constraints === 'object' && constraints.audio)
          ? { ...constraints, audio: RAW_AUDIO_CONSTRAINTS }
          : constraints;
        const stream = await originalGetUserMedia(effectiveConstraints);
        try {
          const track = stream.getAudioTracks?.()[0];
          window.__audioDiag.constraints.push(effectiveConstraints || null);
          if (track) {
            window.__audioDiag.trackSettings.push({
              settings: track.getSettings ? track.getSettings() : null,
              constraints: track.getConstraints ? track.getConstraints() : null,
              label: track.label || null
            });
          }
        } catch (_) {}
        return installObserver(stream);
      };
    }
  });

  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForFunction(() => typeof window.navigateToRoute === 'function' && !!window.miroApi);

  await page.evaluate(async ({ email, password }) => {
    const auth = await window.miroApi.signInWithPassword(email, password);
    const session = auth?.session || await window.miroApi.getSupabaseSession();
    return Boolean(session?.access_token);
  }, { email: EMAIL, password: PASSWORD });

  await page.evaluate(() => window.navigateToRoute('live-setup'));
  await page.waitForFunction(() => document.body.dataset.route === 'live-setup');

  async function clickOptionContains(text) {
    const locator = page.locator('#wire-4-1-live-setup [data-flow-option]').filter({ hasText: text }).first();
    await locator.waitFor({ state: 'visible', timeout: 10000 });
    await locator.click();
    await page.locator('#wire-4-1-live-setup [data-live-flow-next]').click();
  }

  await clickOptionContains('Japan');
  await clickOptionContains('English');
  await clickOptionContains('Saved source');
  await page.locator('#wire-4-1-live-setup [data-live-flow-skip]').click();
  await page.locator('#wire-4-1-live-setup [data-live-flow-start]').click();
  try {
    await page.locator('[data-learning-skip-continue]').click({ timeout: 10000 });
  } catch (_) {}

  await page.waitForFunction(() => document.body.dataset.route === 'live-main', null, { timeout: 30000 });

  const readyStart = Date.now();
  while (!webSockets.some((ws) => ws.frames.some((f) => f.dir === 'recv' && typeof f.raw === 'string' && f.raw.includes('"type": "ready"'))) && Date.now() - readyStart < 30000) {
    await sleep(250);
  }

  await sleep(2000);
  const beforeMarker = Date.now();
  const consoleBeforeIdx = consoleEntries.length;
  const pageErrorsBeforeIdx = pageErrors.length;
  const outBefore = fs.readFileSync(OUT_LOG, 'utf8').split(/\r?\n/);
  const errBefore = fs.readFileSync(ERR_LOG, 'utf8').split(/\r?\n/);

  await sleep(15000);

  const runtime = await page.evaluate(async () => {
    const accessToken = await window.miroApi.getAccessToken();
    return {
      route: document.body.dataset.route,
      voiceStatus: document.querySelector('[data-live-voice-status]')?.textContent?.trim() || null,
      runtimeSessionId: window.appState?.runtimeIds?.sessionId || null,
      currentRoundSessionId: window.appState?.currentRound?.sessionId || null,
      accessTokenPresent: Boolean(accessToken)
    };
  });
  const audioDiag = await page.evaluate(() => window.__audioDiag || null);
  const pageStateAfter = await page.evaluate(() => ({
    voiceStatus: document.querySelector('[data-live-voice-status]')?.textContent?.trim() || null,
    meBubbles: Array.from(document.querySelectorAll('.live-chat-bubble.me')).map((n) => n.textContent.trim()).filter(Boolean),
    aiBubbles: Array.from(document.querySelectorAll('.live-chat-bubble.ai')).map((n) => n.textContent.trim()).filter(Boolean)
  }));

  const outAfter = fs.readFileSync(OUT_LOG, 'utf8').split(/\r?\n/);
  const errAfter = fs.readFileSync(ERR_LOG, 'utf8').split(/\r?\n/);

  const wsDetails = webSockets.map((ws) => ({
    url: ws.url,
    framesBeforeSpeech: ws.frames.filter((f) => f.ts <= beforeMarker).map((f) => ({ dir: f.dir, raw: f.raw, parsed: f.parsed })),
    framesAfterSpeech: ws.frames.filter((f) => f.ts > beforeMarker).map((f) => ({ dir: f.dir, raw: f.raw, parsed: f.parsed })),
    errors: ws.errors,
    closedAt: ws.closedAt
  }));

  const { frameBuffers: wsFrameBuffers, merged: wsMerged, endSegmentSeen } = concatAudioFrames(wsDetails);
  const { frameBuffers, merged } = concatObservedInt16Frames(audioDiag, beforeMarker);
  const { frameBuffers: frameBuffers48, merged: merged48 } = concatObservedPcm48Frames(audioDiag, beforeMarker);
  const { frameBuffers: left48Buffers, merged: left48Merged } = concatObservedNamedFrames(audioDiag, 'leftPcm48Frames', beforeMarker);
  const { frameBuffers: right48Buffers, merged: right48Merged } = concatObservedNamedFrames(audioDiag, 'rightPcm48Frames', beforeMarker);
  writePcm16MonoWav(EXPORTED_WAV, merged, 16000);
  const trimmed = trimSpeechBuffers(frameBuffers);
  writePcm16MonoWav(TRIMMED_WAV, trimmed, 16000);
  writePcm16MonoWav(EXPORTED_WAV_48K, merged48, 48000);
  const trimmed48 = trimSpeechBuffers(frameBuffers48);
  writePcm16MonoWav(TRIMMED_WAV_48K, trimmed48, 48000);
  writePcm16MonoWav(LEFT_WAV_48K, left48Merged, 48000);
  const leftTrimmed48 = trimSpeechBuffers(left48Buffers);
  writePcm16MonoWav(LEFT_TRIMMED_WAV_48K, leftTrimmed48, 48000);
  writePcm16MonoWav(RIGHT_WAV_48K, right48Merged, 48000);
  const rightTrimmed48 = trimSpeechBuffers(right48Buffers);
  writePcm16MonoWav(RIGHT_TRIMMED_WAV_48K, rightTrimmed48, 48000);
  writePcm16MonoWav(WS_EXPORTED_WAV, wsMerged, 16000);
  const wsTrimmed = trimSpeechBuffers(wsFrameBuffers);
  writePcm16MonoWav(WS_TRIMMED_WAV, wsTrimmed, 16000);

  const result = {
    runtime,
    audioDiag,
    floatSummary: summarizeFloatFrames(audioDiag?.floatFrames || []),
    int16Summary: computeInt16Stats(merged),
    wsInt16Summary: computeInt16Stats(wsMerged),
    exportedWav: EXPORTED_WAV,
    exportedTrimmedWav: TRIMMED_WAV,
    exportedWav48k: EXPORTED_WAV_48K,
    exportedTrimmedWav48k: TRIMMED_WAV_48K,
    exportedLeftWav48k: LEFT_WAV_48K,
    exportedLeftTrimmedWav48k: LEFT_TRIMMED_WAV_48K,
    exportedRightWav48k: RIGHT_WAV_48K,
    exportedRightTrimmedWav48k: RIGHT_TRIMMED_WAV_48K,
    exportedWsWav: WS_EXPORTED_WAV,
    exportedWsTrimmedWav: WS_TRIMMED_WAV,
    endSegmentSeen,
    wsDetails,
    consoleAfterSpeech: consoleEntries.slice(consoleBeforeIdx),
    pageErrorsAfterSpeech: pageErrors.slice(pageErrorsBeforeIdx),
    backendOutAfterSpeech: outAfter.slice(outBefore.length).filter(Boolean),
    backendErrAfterSpeech: errAfter.slice(errBefore.length).filter(Boolean),
    pageStateAfter,
    audioPlaybackStarts: audioDiag?.audioPlaybackStarts || []
  };

  fs.writeFileSync(path.join(ROOT, 'tmp_browser_audio_validation_result.json'), JSON.stringify(result, null, 2), 'utf8');
  await browser.close();

  console.log(`BROWSER_AUDIO_VALIDATION_RESULT ${path.join(ROOT, 'tmp_browser_audio_validation_result.json')}`);
})().catch((error) => {
  console.error('BROWSER_AUDIO_VALIDATION_FAILED');
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
