export async function blobToWavFile(blob, fileName = 'voice-note.wav') {
  const audioContext = new AudioContext()
  try {
    const arrayBuffer = await blob.arrayBuffer()
    const decoded = await audioContext.decodeAudioData(arrayBuffer)
    const mono = mixToMono(decoded)
    const wavBuffer = encodeWav(mono, decoded.sampleRate)
    return new File([wavBuffer], fileName, { type: 'audio/wav' })
  } finally {
    await audioContext.close().catch(() => null)
  }
}

function mixToMono(audioBuffer) {
  const output = new Float32Array(audioBuffer.length)

  for (let index = 0; index < audioBuffer.length; index += 1) {
    let total = 0
    for (let channel = 0; channel < audioBuffer.numberOfChannels; channel += 1) {
      total += audioBuffer.getChannelData(channel)[index] ?? 0
    }
    output[index] = total / audioBuffer.numberOfChannels
  }

  return output
}

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)

  writeAscii(view, 0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  writeAscii(view, 8, 'WAVE')
  writeAscii(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeAscii(view, 36, 'data')
  view.setUint32(40, samples.length * 2, true)

  let offset = 44
  for (let index = 0; index < samples.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, samples[index]))
    view.setInt16(offset, sample < 0 ? sample * 32768 : sample * 32767, true)
    offset += 2
  }

  return buffer
}

function writeAscii(view, offset, text) {
  for (let index = 0; index < text.length; index += 1) {
    view.setUint8(offset + index, text.charCodeAt(index))
  }
}