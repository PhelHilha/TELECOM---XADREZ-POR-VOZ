# -*- coding: utf-8 -*-

import os
import sys
import time
import queue
import pygame
import chess
import vosk
import pyaudio
import json
import re

from ui_renderer import UIRenderer
from game_logic import GameState
from bot_handler import BotHandler

# constantes principais
FPS = 30

# Crie esta lista no início do seu código, antes de inicializar o Vosk.

lista_vocabulario_xadrez = [
    # Comandos
    "mover", "mova", "jogar", "para",

    # Peças
    "peão", "torre", "cavalo", "bispo", "rainha", "rei",

    # Casas (escritas como falamos para maior precisão)
    "a um", "a dois", "a três", "a quatro", "a cinco", "a seis", "a sete", "a oito",
    "b um", "b dois", "b três", "b quatro", "b cinco", "b seis", "b sete", "b oito",
    "c um", "c dois", "c três", "c quatro", "c cinco", "c seis", "c sete", "c oito",
    "d um", "d dois", "d três", "d quatro", "d cinco", "d seis", "d sete", "d oito",
    "e um", "e dois", "e três", "e quatro", "e cinco", "e seis", "e sete", "e oito",
    "f um", "f dois", "f três", "f quatro", "f cinco", "f seis", "f sete", "f oito",
    "g um", "g dois", "g três", "g quatro", "g cinco", "g seis", "g sete", "g oito",
    "h um", "h dois", "h três", "h quatro", "h cinco", "h seis", "h sete", "h oito",

    "[unk]"
]
def parse_voice_command(text: str) -> chess.Move | None:
    """
    Interpreta o texto reconhecido, que pode conter números por extenso
    (ex: "dois"), e tenta extrair um movimento de xadrez no formato UCI.
    Retorna um objeto chess.Move ou None.
    """
    # 1. Dicionário para mapear o número falado para o dígito correspondente.
    numeros_por_extenso = {
        "um": "1", "dois": "2", "três": "3", "quatro": "4",
        "cinco": "5", "seis": "6", "sete": "7", "oito": "8"
    }
    
    # Cria uma parte da regex dinamicamente para incluir todos os números.
    # Isso resultará em "(um|dois|três|...|oito)"
    numeros_regex = "|".join(numeros_por_extenso.keys())

    # 2. Expressão regular aprimorada.
    # Agora ela captura a letra e o número falado separadamente.
    # Ex: Para "g um", captura "g" e "um".
    padrao = re.compile(
        r"mover .* ([a-h]) (" + numeros_regex + r") para ([a-h]) (" + numeros_regex + r")", 
        re.IGNORECASE
    )
    
    match = padrao.search(text)
    
    if match:
        # A regex agora captura 4 grupos:
        # (letra_origem, numero_falado_origem, letra_destino, numero_falado_destino)
        letra_origem, num_falado_origem, letra_destino, num_falado_destino = match.groups()

        # 3. Lógica de conversão.
        # Usa o dicionário para obter os dígitos.
        digito_origem = numeros_por_extenso.get(num_falado_origem.lower())
        digito_destino = numeros_por_extenso.get(num_falado_destino.lower())

        # Verifica se a conversão funcionou (segurança extra)
        if not (digito_origem and digito_destino):
            return None

        # Monta a string UCI final (ex: "g1f3")
        uci_move = f"{letra_origem}{digito_origem}{letra_destino}{digito_destino}"
        
        print(f"Comando de voz processado: '{text}' -> Movimento UCI: '{uci_move}'")

        try:
            # Lógica simples para promoção de peão (sempre promove para rainha 'q')
            # Você pode tornar isso mais sofisticado depois, se quiser.
            if (digito_origem == '7' and digito_destino == '8') or \
               (digito_origem == '2' and digito_destino == '1'):
                # Precisamos verificar se a peça é um peão, mas a string UCI não tem essa info.
                # A validação `if move in board.legal_moves` no loop principal cuidará disso.
                # Se for uma jogada de promoção legal, o motor de xadrez exigirá o sufixo.
                uci_move += 'q'

            return chess.Move.from_uci(uci_move)
        except ValueError:
            return None
            
    return None


def main():
    pygame.init()
    BASE_DIR = os.path.dirname(__file__)
    tela = pygame.display.set_mode((1024, 768))
    pygame.display.set_caption("Xadrez - Não bloqueante")
    clock = pygame.time.Clock()

    ui = UIRenderer(tela,
                    caminho_imagens=os.path.join(BASE_DIR, "imagens"),
                    caminho_sons=os.path.join(BASE_DIR, "assets", "sounds"))
    state = GameState()
    bot = BotHandler(path=os.path.join(BASE_DIR, "stockfish.exe"), default_think_ms=2000)

    estado_jogo = "MENU_PRINCIPAL"  # MENU_PRINCIPAL, MENU_DIFICULDADE, MENU_COR, MENU_TEMPO, JOGANDO, FIM_DE_JOGO
    modo_jogo = None  # "pvp" or "pvb"
    cor_jogador = None  # chess.WHITE or chess.BLACK (quando pvb)
    tabuleiro_invertido = False
    skill_bot = None

    # timers
    tempo_inicial = None
    tempo_brancas = None
    tempo_pretas = None
    ultimo_update_relogio = pygame.time.get_ticks()


    # fila para pensamento do bot
    bot_result_queue = None
    
        # ---------- CONFIGURAÇÃO DO VOSK E PYAUDIO ----------
    MODEL_PATH = "vosk-model-small-pt-0.3"  # <-- MUDE AQUI para o nome da sua pasta de modelo
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 8192
    
    # Validação do caminho do modelo
    if not os.path.exists(MODEL_PATH):
        print(f"ERRO: O diretório do modelo Vosk '{MODEL_PATH}' não foi encontrado.")
        print("Por favor, baixe o modelo e coloque-o no diretório correto.")
        pygame.quit()
        sys.exit()

    # Inicialização
    try:
        model = vosk.Model(MODEL_PATH)
        recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE, json.dumps(lista_vocabulario_xadrez, ensure_ascii=False))
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=SAMPLE_RATE,
                        input=True,
                        frames_per_buffer=CHUNK_SIZE)
        stream.start_stream()
        print(">>> Ouvindo para comandos de voz...")
    except Exception as e:
        print(f"Ocorreu um erro ao inicializar o áudio: {e}")
        # Desabilita o controle de voz se houver erro
        stream = None

    # loop principal
    rodando = True
    while rodando:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                rodando = False
                break

            # ---------- MENUS ----------
            if estado_jogo == "MENU_PRINCIPAL":
                pvp_rect, pvb_rect = ui.draw_menu_principal()  # desenha e devolve rects
                escolha = ui.handle_menu_principal_event(event, pvp_rect, pvb_rect)
                if escolha == "pvp":
                    modo_jogo = "pvp"
                    estado_jogo = "MENU_TEMPO"
                elif escolha == "pvb":
                    modo_jogo = "pvb"
                    estado_jogo = "MENU_DIFICULDADE"

            elif estado_jogo == "MENU_DIFICULDADE":
                ui.draw_menu_dificuldade()
                escolha = ui.handle_menu_dificuldade_event(event)
                if escolha is not None:
                    # escolha: tuple(skill_value, label) or None
                    skill_bot = escolha
                    estado_jogo = "MENU_COR"

            elif estado_jogo == "MENU_COR":
                ui.draw_menu_cor()
                escolha = ui.handle_menu_cor_event(event)
                if escolha is not None:
                    # escolha: chess.WHITE or chess.BLACK
                    cor_jogador = escolha
                    estado_jogo = "MENU_TEMPO"

            elif estado_jogo == "MENU_TEMPO":
                botoes = ui.draw_menu_tempo()
                escolha = ui.handle_menu_tempo_event(event, botoes)
                if escolha is not None:
                    # escolha é segundos ou None (sem tempo)
                    tempo_inicial = time.time()
                    tempo_brancas = escolha if escolha is not None else None
                    tempo_pretas = escolha if escolha is not None else None
                    state.reset_game()
                    # se PVB e jogador escolheu cor, set bot skill
                    if modo_jogo == "pvb" and skill_bot is not None:
                        bot.configure_skill(skill_bot)
                    # se for PVB e cor_jogador é preto, bot pensa primeiro
                    if modo_jogo == "pvb" and cor_jogador is not None and state.board.turn != cor_jogador:
                        bot_result_queue = bot.start_thinking(state.board.fen(), result_q=None, think_ms=bot.think_time_ms)
                    estado_jogo = "JOGANDO"

            # ---------- JOGANDO: eventos de jogo (não bloqueante) ----------
            elif estado_jogo == "JOGANDO":
                # passamos o event para o handler de jogo; ele pode retornar um move (chess.Move) ou None
                result = ui.handle_jogo_event(event, state, tabuleiro_invertido, cor_jogador, modo_jogo)
                if isinstance(result, chess.Move):
                    # aplicar jogada do jogador
                    # Se for promoção, handle_jogo_event retorna a jogada já com promotion set (se seleção foi feita)
                    if result in state.board.legal_moves:
                        # antes de push, podemos tocar som dentro de UI
                        state.push_move(result)
                        ui.play_sound_for_move(state.board, result)
                        # se agora for vez do bot, iniciar thinking sem bloquear
                        if modo_jogo == "pvb" and state.board.turn != cor_jogador and not state.board.is_game_over():
                            bot_result_queue = bot.start_thinking(state.board.fen(), result_q=None, think_ms=bot.think_time_ms)
 
                # se handler retornou special commands
                elif result == "DESISTIR":
                    vencedor = "Pretas" if state.board.turn == chess.WHITE else "Brancas"
                    state.resultado_final = f"{vencedor} venceram por desistência."
                    estado_jogo = "FIM_DE_JOGO"

            # ---------- FIM DE JOGO ----------
            elif estado_jogo == "FIM_DE_JOGO":
                escolha = ui.handle_fim_event(event)
                if escolha == "REINICIAR":
                    estado_jogo = "MENU_PRINCIPAL"
                    state.reset_game()


        # ----- processar áudio do microfone (Vosk) -----
        if stream and estado_jogo == "JOGANDO":
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                result_json = json.loads(recognizer.Result())
                text = result_json.get("text", "")
                print(text)

                if text:
                    voice_move = parse_voice_command(text)
                    
                    # Se o comando de voz gerou um movimento válido e é a vez do jogador
                    if (voice_move is not None and 
                        voice_move in state.board.legal_moves and
                        (modo_jogo == "pvp" or state.board.turn == cor_jogador)):

                        state.push_move(voice_move)
                        ui.play_sound_for_move(state.board, voice_move)
                        
                        # Se for a vez do bot, inicia o pensamento dele
                        if modo_jogo == "pvb" and state.board.turn != cor_jogador and not state.board.is_game_over():
                            bot_result_queue = bot.start_thinking(state.board.fen(), result_q=None, think_ms=bot.think_time_ms)
                            
                            
        # ----- atualização dos relógios (sempre decrementar o jogador que está com a vez) -----
        now_ticks = pygame.time.get_ticks()
        if estado_jogo == "JOGANDO" and tempo_inicial is not None:
            delta_ms = now_ticks - ultimo_update_relogio
            ultimo_update_relogio = now_ticks
            if state.board.turn == chess.WHITE:
                if tempo_brancas is not None:
                    tempo_brancas -= delta_ms / 1000.0
            else:
                if tempo_pretas is not None:
                    tempo_pretas -= delta_ms / 1000.0

            if tempo_brancas is not None and tempo_brancas <= 0:
                state.resultado_final = "Pretas venceram no tempo!"
                estado_jogo = "FIM_DE_JOGO"
            elif tempo_pretas is not None and tempo_pretas <= 0:
                state.resultado_final = "Brancas venceram no tempo!"
                estado_jogo = "FIM_DE_JOGO"

        else:
            # atualizar tick reference
            ultimo_update_relogio = now_ticks

        # ----- processar resultado do bot (poll não-bloqueante) -----
        if estado_jogo == "JOGANDO" and modo_jogo == "pvb" and bot_result_queue is not None:
            try:
                mv_uci = bot_result_queue.get_nowait()
            except queue.Empty:
                mv_uci = None
            if mv_uci is not None:
                if mv_uci:
                    try:
                        mv = chess.Move.from_uci(mv_uci)
                        if mv in state.board.legal_moves:
                            state.push_move(mv)
                            ui.play_sound_for_move(state.board, mv)
                        else:
                            # fallback: jogada legal aleatória
                            import random
                            legal = list(state.board.legal_moves)
                            if legal:
                                mv2 = random.choice(legal)
                                state.push_move(mv2)
                                ui.play_sound_for_move(state.board, mv2)
                    except Exception as e:
                        print("Erro ao aplicar jogada do bot:", e)
                bot_result_queue = None

        # ----- checar fim de jogo pelo tabuleiro -----
        if estado_jogo == "JOGANDO" and state.board.is_game_over():
            if state.board.is_checkmate():
                vencedor = "Pretas" if state.board.turn == chess.WHITE else "Brancas"
                state.resultado_final = f"Xeque-mate! {vencedor} venceram."
            else:
                state.resultado_final = "Empate!"
            estado_jogo = "FIM_DE_JOGO"

        # ----- RENDER -----
        if estado_jogo == "MENU_PRINCIPAL":
            ui.draw_menu_principal()
        elif estado_jogo == "MENU_DIFICULDADE":
            ui.draw_menu_dificuldade()
        elif estado_jogo == "MENU_COR":
            ui.draw_menu_cor()
        elif estado_jogo == "MENU_TEMPO":
            ui.draw_menu_tempo()
        else:
            ultimo_mov = state.board.peek() if state.board.move_stack else None
            ui.draw_board(state.board, tabuleiro_invertido, state.quadrado_selecionado, ultimo_mov)
            ui.draw_panel_info(state.board, tempo_brancas, tempo_pretas, state.historico_san, modo_jogo, skill_bot, cor_jogador)
            if estado_jogo == "FIM_DE_JOGO":
                ui.draw_end_screen(state.resultado_final)

        pygame.display.flip()

    # saída limpa
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
