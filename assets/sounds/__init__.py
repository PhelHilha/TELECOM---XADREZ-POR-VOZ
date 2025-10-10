import pygame
pygame.mixer.init()

sons = {
    'move': pygame.mixer.Sound('assets/sounds/move.wav'),
    'capture': pygame.mixer.Sound('assets/sounds/capture.wav'),
    'check': pygame.mixer.Sound('assets/sounds/check.wav')
}

def play_sound(nome):
    try:
        sons[nome].play()
    except Exception as e:
        print(f"Erro ao tocar som {nome}: {e}")