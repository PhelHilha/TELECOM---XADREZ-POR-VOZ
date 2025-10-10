import vosk
import pyaudio
import json

# Lista de palavras e frases que você quer reconhecer
comandos_especificos = [
    "e6", 
    "fechar programa", 
    "aumentar volume", 
    "diminuir volume", 
    "cavalo",
    "batata voadora",
    "[unk]"  # Opcional: para capturar palavras desconhecidas
]

# Converte a lista para o formato JSON, que é o que o Vosk espera
comandos_json = json.dumps(comandos_especificos)

MODEL_PATH = "vosk-model-small-pt-0.3" 

try:
    model = vosk.Model(MODEL_PATH)
except Exception as e:
    print(f"Erro ao carregar o modelo: {e}")
    exit(1)

# A MUDANÇA É AQUI: passe a lista de comandos como terceiro argumento
recognizer = vosk.KaldiRecognizer(model, 16000, comandos_json)

# O resto do código permanece o mesmo
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=8192)

print("Aguardando comandos específicos...")

try:
    while True:
        data = stream.read(4096, exception_on_overflow=False)
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            if result['text']:
                print(f"Comando detectado: {result['text']}")

except KeyboardInterrupt:
    print("\nParando o reconhecimento.")

finally:
    stream.stop_stream()
    stream.close()
    p.terminate()