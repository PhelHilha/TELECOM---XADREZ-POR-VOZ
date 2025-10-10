import os
import sys
import time
import queue
import pygame
import chess

from ui_renderer import UIRenderer
from game_logic import GameState
from bot_handler import BotHandler

# constantes principais
FPS = 30

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
