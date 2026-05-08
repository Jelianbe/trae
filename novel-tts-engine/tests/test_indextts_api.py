import requests
import os

r = requests.post('http://localhost:8300/v2/synthesize', json={
    'text': '你好，世界',
    'audio_path': 'D:/trae/novel-tts-engine/TTS/IndexTTS2-SonicVale/examples/voice_01.wav'
})
print(f'Status: {r.status_code}')
print(f'Content-Type: {r.headers.get("content-type", "N/A")}')
print(f'Content-Length: {len(r.content)} bytes')

fname = 'D:/trae/novel-tts-engine/tests/output/indextts_api_test.wav'
os.makedirs(os.path.dirname(fname), exist_ok=True)
with open(fname, 'wb') as f:
    f.write(r.content)
print(f'Saved to: {fname}')

import soundfile as sf
data, sr = sf.read(fname)
print(f'Duration: {len(data)/sr:.2f}s, Sample rate: {sr}')
print('INDEX TTS API WORKS!')
