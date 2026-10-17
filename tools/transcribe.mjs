// Пословная транскрибация локальным Whisper (ONNX, без интернета).
// usage: node transcribe.mjs <audio.f32 (16kHz mono float32le)> <out.json> [language] [model]
import { pipeline, env } from '@huggingface/transformers';
import fs from 'fs';
import { createRequire } from 'module';
import path from 'path';

const [input, output, language = 'russian', model = 'small'] = process.argv.slice(2);
const require = createRequire(import.meta.url);
const pkgDir = path.dirname(require.resolve(`sts-whisper-${model}/package.json`));
env.localModelPath = path.join(pkgDir, 'models') + '/';
env.allowRemoteModels = false;

const asr = await pipeline('automatic-speech-recognition', `Xenova/whisper-${model}`, { dtype: 'q8' });
const buf = fs.readFileSync(input);
const audio = new Float32Array(buf.buffer, buf.byteOffset, Math.floor(buf.length / 4));
const out = await asr(audio, {
  language: language === 'auto' ? undefined : language,
  task: 'transcribe',
  return_timestamps: 'word',
  chunk_length_s: 30,
  stride_length_s: 5,
});
const words = (out.chunks || [])
  .map(c => ({ w: c.text.trim(), s: c.timestamp[0], e: c.timestamp[1] ?? c.timestamp[0] + 0.3 }))
  .filter(x => x.w);
fs.writeFileSync(output, JSON.stringify({ text: out.text.trim(), words }, null, 1));
