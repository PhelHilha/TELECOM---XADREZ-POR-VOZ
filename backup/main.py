# main.py (parte relevante: loop principal e integração não-bloqueante do bot)
import os
import sys
import time
import queue
import pygame
import chess
from ui_renderer import UIRenderer
from game_logic import GameState
from bot_handler import BotHandler

# caminhos e constantes (ajuste conforme seu projeto)
NOME_EXECUTAVEL_STOCKFISH = "stockfish.exe"
CAMINHO_IMAGENS = "imagens"
CAMINHO_SONS = os.path.join("assets", "sounds")
FPS = 30
BOT_THINK_MS = 2000  # 2 segundos de pensamento

def main():
    pygame.init()
    tela = pygame.display.set_mode((880, 640))
    pygame.display.set_caption("Xadrez - Correção Bot Não-Bloqueante")
    clock = pygame.time.Clock()

    ui = UIRenderer(tela, caminho_imagens=CAMINHO_IMAGENS, caminho_sons=CAMINHO_SONS)
    state = GameState()
    bot = BotHandler(path=NOME_EXECUTAVEL_STOCKFISH, default_think_ms=BOT_THINK_MS)
    bot.set_think_time(BOT_THINK_MS)

    estado_jogo = "MENU_PRINCIPAL"
    modo_jogo = None
    cor_jogador = None
    tabuleiro_invertido = False
    skill_bot = None
    tempo_inicial = None
    tempo_brancas = None
    tempo_pretas = None
    ultimo_update_relogio = pygame.time.get_ticks()

    # fila para comunicação com o thread do bot
    bot_result_queue = None

    while True:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # (aqui você mantém sua lógica de menus igual ao seu main.py original,
            #  não vou reescrever todos os menus para não confundir — assuma que
            #  eles setam modo_jogo, cor_jogador, skill_bot, etc, como antes)
            #
            # Exemplo resumido para MENU_PRINCIPAL:
            if estado_jogo == "MENU_PRINCIPAL":
                pvp_rect, pvb_rect = ui.draw_menu_principal()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if pvp_rect.collidepoint(event.pos):
                        modo_jogo = "pvp"; estado_jogo = "MENU_TEMPO"
                    elif pvb_rect.collidepoint(event.pos):
                        estado_jogo = "MENU_DIFICULDADE"
            # ... trate os outros menus aqui conforme já tem no seu código ...

            # Quando estiver jogando: clique do jogador -> aplicar imediatamente
            if estado_jogo == "JOGANDO" and event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                # clique no painel desistir (mesma geometria do seu UI)
                desistir_rect = pygame.Rect(880 - (880-640) + 20, 640 - 60, (880-640) - 40, 40)
                if desistir_rect.collidepoint(pos):
                    vencedor = "Pretas" if state.board.turn == chess.WHITE else "Brancas"
                    state.resultado_final = f"{vencedor} venceram por desistência."
                    estado_jogo = "FIM_DE_JOGO"
                elif pos[0] <= 640:
                    tela_c, tela_r = pos[0] // (640//8), pos[1] // (640//8)
                    if tabuleiro_invertido:
                        quadrado = chess.square(7 - tela_c, tela_r)
                    else:
                        quadrado = chess.square(tela_c, 7 - tela_r)

                    # seleção / movimento (igual lógica anterior)
                    if not state.cliques_jogador:
                        p = state.board.piece_at(quadrado)
                        if p and p.color == state.board.turn:
                            state.quadrado_selecionado = quadrado
                            state.cliques_jogador = [quadrado]
                    else:
                        p2 = state.board.piece_at(quadrado)
                        if p2 and p2.color == state.board.turn:
                            state.quadrado_selecionado = quadrado
                            state.cliques_jogador = [quadrado]
                        else:
                            mv = chess.Move(state.cliques_jogador[0], quadrado)
                            # promoção modal (se necessário)
                            if state.board.piece_type_at(state.cliques_jogador[0]) == chess.PAWN and chess.square_rank(quadrado) in [0,7]:
                                promo = ui.promotion_modal(state.board.turn == chess.WHITE)
                                if promo:
                                    mv.promotion = promo
                            if mv in state.board.legal_moves:
                                # **APLICA A JOGADA DO JOGADOR IMEDIATAMENTE**
                                state.push_move(mv)
                                ui.play_sound_for_move(state.board, mv)   # tocar som
                                # limpar seleção
                                state.quadrado_selecionado = None
                                state.cliques_jogador = []

                                # se agora é vez do bot, iniciar thinking em background
                                if modo_jogo == "pvb" and state.board.turn != cor_jogador and not state.board.is_game_over():
                                    # cria/usa fila e inicia worker do bot
                                    bot_result_queue = bot.start_thinking(state.board.fen(), result_q=None, think_ms=bot.think_time_ms)

        # ----- atualização de tempo (sempre decrementar o jogador cujo turno é atual) -----
        if estado_jogo == "JOGANDO" and tempo_inicial is not None:
            now = pygame.time.get_ticks()
            delta_ms = now - ultimo_update_relogio
            ultimo_update_relogio = now

            # decrementar sempre o relógio do lado que está em 'board.turn'
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

        # ----- processar resultado do bot (se tiver) -----
        if estado_jogo == "JOGANDO" and modo_jogo == "pvb" and bot_result_queue is not None:
            try:
                # poll não-bloqueante: se tiver resultado, aplicar
                mv_uci = bot_result_queue.get_nowait()
            except queue.Empty:
                mv_uci = None
            if mv_uci is not None:
                # aplicar jogada do bot no thread principal
                if mv_uci:
                    try:
                        mv = chess.Move.from_uci(mv_uci)
                        if mv in state.board.legal_moves:
                            state.push_move(mv)
                            ui.play_sound_for_move(state.board, mv)
                        else:
                            # caso engine retorne jogada ilegal por algum motivo,
                            # tente aplicar fallback: jogada legal aleatória
                            import random
                            legal = list(state.board.legal_moves)
                            if legal:
                                mv2 = random.choice(legal)
                                state.push_move(mv2)
                                ui.play_sound_for_move(state.board, mv2)
                    except Exception as e:
                        print("Erro ao aplicar jogada do bot:", e)
                # limpar a fila/flag para permitir nova invocação posteriormente
                bot_result_queue = None

        # checar fim de jogo (tabuleiro)
        if estado_jogo == "JOGANDO" and state.board.is_game_over():
            if state.board.is_checkmate():
                vencedor = "Pretas" if state.board.turn == chess.WHITE else "Brancas"
                state.resultado_final = f"Xeque-mate! {vencedor} venceram."
            else:
                state.resultado_final = "Empate!"
            estado_jogo = "FIM_DE_JOGO"

        # ----- render (mantém sua UI antiga) -----
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

if __name__ == "__main__":
    main()
