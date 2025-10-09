# xadrez_completo_v5.py

import pygame
import chess
import sys
import os
from stockfish import Stockfish
import math

# --- CONFIGURAÇÃO INICIAL ---
NOME_EXECUTAVEL_STOCKFISH = "stockfish.exe" # <-- MUDE AQUI SE NECESSÁRIO
CAMINHO_IMAGENS = "imagens/" # Pasta onde as imagens estão

# --- Constantes e Configuração do Pygame ---
LARGURA_TELA, ALTURA_TELA = 880, 640
LARGURA_TABULEIRO, ALTURA_TABULEIRO = 640, 640
DIMENSAO = 8
TAMANHO_QUADRADO = LARGURA_TABULEIRO // DIMENSAO
LARGURA_PAINEL = LARGURA_TELA - LARGURA_TABULEIRO

# Cores e Fontes
pygame.init()
COR_CLARA = pygame.Color(238, 238, 210)
COR_ESCURA = pygame.Color(118, 150, 86)
COR_DESTAQUE_SELECAO = pygame.Color(255, 255, 51, 150)
COR_DESTAQUE_ULTIMO_MOV = pygame.Color(170, 162, 58, 150)
COR_DESTAQUE_VALIDO = pygame.Color(0, 0, 0, 60)
COR_PAINEL = pygame.Color("gray20")
COR_TEXTO = pygame.Color("white")
COR_BOTAO = pygame.Color("gray30")
COR_BOTAO_DESISTIR = pygame.Color(180, 60, 60)
COR_RELOGIO_ATIVO = pygame.Color(120, 190, 120)

FONTE_PECAS_NOME = "Segoe UI Symbol"
FONTE_PECAS = pygame.font.SysFont(FONTE_PECAS_NOME, int(TAMANHO_QUADRADO * 0.8))
FONTE_PAINEL_TITULO = pygame.font.SysFont("helvetica", 32)
FONTE_PAINEL_TEXTO = pygame.font.SysFont("helvetica", 24)
FONTE_COORDENADAS = pygame.font.SysFont("helvetica", 16)
FONTE_MENU = pygame.font.SysFont("helvetica", 50)
FONTE_RELOGIO = pygame.font.SysFont("monospace", 40, bold=True)
FONTE_LABEL = pygame.font.SysFont("helvetica", 20, bold=True) # Nova fonte para labels "Adversário"/"Jogador"


# Dicionário Unicode para as peças
PECAS_UNICODE = { 'P': '♙', 'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'p': '♟', 'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚' }

# --- Carregamento de Imagens ---
IMAGENS_BOT = {
    "Bagre": pygame.image.load(os.path.join(CAMINHO_IMAGENS, "bagre.jpeg")),
    "Joi": pygame.image.load(os.path.join(CAMINHO_IMAGENS, "joi.jpeg")),
    "Mr Chess": pygame.image.load(os.path.join(CAMINHO_IMAGENS, "mr_chess.jpg"))
}
IMAGEM_JOGADOR = pygame.image.load(os.path.join(CAMINHO_IMAGENS, "jogador.jpeg"))

# Tamanho padrão para as imagens dos avatares
TAMANHO_AVATAR = (80, 80)
for key in IMAGENS_BOT:
    IMAGENS_BOT[key] = pygame.transform.scale(IMAGENS_BOT[key], TAMANHO_AVATAR)
IMAGEM_JOGADOR = pygame.transform.scale(IMAGEM_JOGADOR, TAMANHO_AVATAR)


# --- Funções Auxiliares e de Desenho ---

def formatar_tempo(segundos):
    if segundos is None or segundos < 0: return "--:--"
    minutos = math.floor(segundos / 60)
    segundos_restantes = math.floor(segundos % 60)
    return f"{minutos:02d}:{segundos_restantes:02d}"

def desenhar_texto(tela, texto, fonte, cor, centro_rect):
    obj_texto = fonte.render(texto, True, cor)
    rect_texto = obj_texto.get_rect(center=centro_rect)
    tela.blit(obj_texto, rect_texto)

def desenhar_tabuleiro(tela, tabuleiro_invertido):
    for r in range(DIMENSAO):
        for c in range(DIMENSAO):
            cor_quadrado = COR_CLARA if (r + c) % 2 == 0 else COR_ESCURA
            pygame.draw.rect(tela, cor_quadrado, pygame.Rect(c * TAMANHO_QUADRADO, r * TAMANHO_QUADRADO, TAMANHO_QUADRADO, TAMANHO_QUADRADO))
            if tabuleiro_invertido: quadrado_real = chess.square(7 - c, r)
            else: quadrado_real = chess.square(c, 7 - r)
            cor_texto_coord = COR_ESCURA if (r + c) % 2 == 0 else COR_CLARA
            coordenada = chess.SQUARE_NAMES[quadrado_real]
            texto_coord = FONTE_COORDENADAS.render(coordenada, True, cor_texto_coord)
            tela.blit(texto_coord, (c * TAMANHO_QUADRADO + 2, r * TAMANHO_QUADRADO + 2))

def desenhar_pecas(tela, board, tabuleiro_invertido):
    for i in range(64):
        peca = board.piece_at(i)
        if peca:
            rank_real, file_real = chess.square_rank(i), chess.square_file(i)
            if tabuleiro_invertido: r, c = rank_real, 7 - file_real
            else: r, c = 7 - rank_real, file_real
            simbolo, cor_peca = PECAS_UNICODE[peca.symbol()], pygame.Color('black') if peca.color == chess.BLACK else pygame.Color('white')
            texto_sombra, texto_peca = FONTE_PECAS.render(simbolo, True, pygame.Color('gray20')), FONTE_PECAS.render(simbolo, True, cor_peca)
            pos_x, pos_y = c * TAMANHO_QUADRADO + (TAMANHO_QUADRADO - texto_peca.get_width()) // 2, r * TAMANHO_QUADRADO + (TAMANHO_QUADRADO - texto_peca.get_height()) // 2
            for offset in [(1, 1), (1, -1), (-1, 1), (-1, -1)]: tela.blit(texto_sombra, (pos_x + offset[0], pos_y + offset[1]))
            tela.blit(texto_peca, (pos_x, pos_y))

def desenhar_destaques(tela, board, quadrado_selecionado, ultimo_mov, tabuleiro_invertido):
    s = pygame.Surface((TAMANHO_QUADRADO, TAMANHO_QUADRADO), pygame.SRCALPHA)
    def get_pos_tela(quadrado):
        rank, file = chess.square_rank(quadrado), chess.square_file(quadrado)
        if tabuleiro_invertido: return rank, 7 - file
        else: return 7 - rank, file
    if ultimo_mov:
        s.fill(COR_DESTAQUE_ULTIMO_MOV)
        for quadrado in [ultimo_mov.from_square, ultimo_mov.to_square]:
            r, c = get_pos_tela(quadrado)
            tela.blit(s, (c * TAMANHO_QUADRADO, r * TAMANHO_QUADRADO))
    if quadrado_selecionado is not None:
        s.fill(COR_DESTAQUE_SELECAO)
        r, c = get_pos_tela(quadrado_selecionado)
        tela.blit(s, (c * TAMANHO_QUADRADO, r * TAMANHO_QUADRADO))
        s.fill(COR_DESTAQUE_VALIDO)
        for move in board.legal_moves:
            if move.from_square == quadrado_selecionado:
                r_dest, c_dest = get_pos_tela(move.to_square)
                centro = (c_dest * TAMANHO_QUADRADO + TAMANHO_QUADRADO // 2, r_dest * TAMANHO_QUADRADO + TAMANHO_QUADRADO // 2)
                pygame.draw.circle(tela, s.get_at((0,0)), centro, 15)

def desenhar_painel_info(tela, board, tempo_brancas, tempo_pretas, historico_san, modo_jogo, skill_bot, cor_jogador):
    pygame.draw.rect(tela, COR_PAINEL, pygame.Rect(LARGURA_TABULEIRO, 0, LARGURA_PAINEL, ALTURA_TELA))
    
    centro_x_painel = LARGURA_TABULEIRO + LARGURA_PAINEL // 2
    
    # --- Seção Superior (Adversário) ---
    y_pos = 20
    desenhar_texto(tela, "Adversário", FONTE_LABEL, COR_TEXTO, (centro_x_painel, y_pos))
    y_pos += 30

    avatar_oponente_img = None
    if modo_jogo == "pvp":
        # Em PvP, o adversário é simplesmente a outra cor.
        avatar_oponente_img = IMAGEM_JOGADOR # Usamos uma imagem genérica ou a mesma.
    elif modo_jogo == "pvb":
        if skill_bot == 0: avatar_oponente_img = IMAGENS_BOT["Bagre"]
        elif skill_bot == 3: avatar_oponente_img = IMAGENS_BOT["Joi"]
        elif skill_bot == 7: avatar_oponente_img = IMAGENS_BOT["Mr Chess"]
    
    if avatar_oponente_img:
        avatar_rect = avatar_oponente_img.get_rect(center=(centro_x_painel, y_pos + TAMANHO_AVATAR[1] // 2))
        tela.blit(avatar_oponente_img, avatar_rect)
        y_pos = avatar_rect.bottom + 10

    cor_relogio_oponente = COR_RELOGIO_ATIVO if board.turn != cor_jogador else COR_BOTAO
    rect_relogio_oponente = pygame.Rect(LARGURA_TABULEIRO + 10, y_pos, LARGURA_PAINEL - 20, 45)
    pygame.draw.rect(tela, cor_relogio_oponente, rect_relogio_oponente, border_radius=10)
    desenhar_texto(tela, formatar_tempo(tempo_pretas if cor_jogador == chess.WHITE else tempo_brancas), FONTE_RELOGIO, COR_TEXTO, rect_relogio_oponente.center)
    y_pos = rect_relogio_oponente.bottom + 20

    # --- Seção Inferior (Jogador) ---
    # Posicionamento de baixo para cima para garantir que tudo caiba
    y_pos_inferior = ALTURA_TELA - 20
    desistir_rect = pygame.Rect(LARGURA_TABULEIRO + 20, y_pos_inferior - 40, LARGURA_PAINEL - 40, 40)
    pygame.draw.rect(tela, COR_BOTAO_DESISTIR, desistir_rect, border_radius=10)
    desenhar_texto(tela, "Desistir", FONTE_PAINEL_TEXTO, COR_TEXTO, desistir_rect.center)
    y_pos_inferior = desistir_rect.top - 10
    
    cor_relogio_jogador = COR_RELOGIO_ATIVO if board.turn == cor_jogador else COR_BOTAO
    rect_relogio_jogador = pygame.Rect(LARGURA_TABULEIRO + 10, y_pos_inferior - 45, LARGURA_PAINEL - 20, 45)
    pygame.draw.rect(tela, cor_relogio_jogador, rect_relogio_jogador, border_radius=10)
    desenhar_texto(tela, formatar_tempo(tempo_brancas if cor_jogador == chess.WHITE or modo_jogo == "pvp" else tempo_pretas), FONTE_RELOGIO, COR_TEXTO, rect_relogio_jogador.center)
    y_pos_inferior = rect_relogio_jogador.top - 10

    avatar_jogador_rect = IMAGEM_JOGADOR.get_rect(center=(centro_x_painel, y_pos_inferior - TAMANHO_AVATAR[1] // 2))
    tela.blit(IMAGEM_JOGADOR, avatar_jogador_rect)
    y_pos_inferior = avatar_jogador_rect.top - 5

    desenhar_texto(tela, "Jogador", FONTE_LABEL, COR_TEXTO, (centro_x_painel, y_pos_inferior - 15))


    # --- Histórico de Movimentos (Ocupa o espaço restante no meio) ---
    desenhar_texto(tela, "Histórico", FONTE_PAINEL_TEXTO, COR_TEXTO, (centro_x_painel, y_pos))
    y_pos += 25
    for i, texto_mov in enumerate(historico_san):
        if y_pos + (i * 25) < y_pos_inferior - 40: # Verifica se há espaço
            desenhar_texto(tela, texto_mov, FONTE_PAINEL_TEXTO, COR_TEXTO, (centro_x_painel, y_pos + i * 25))

    return desistir_rect

def desenhar_tela_fim_de_jogo(tela, resultado):
    s, botao_rect = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA), pygame.Rect(LARGURA_TELA // 2 - 150, ALTURA_TELA // 2, 300, 80)
    s.fill((0, 0, 0, 180))
    tela.blit(s, (0, 0))
    desenhar_texto(tela, resultado, FONTE_MENU, "gold", (LARGURA_TELA // 2, ALTURA_TELA // 3))
    pygame.draw.rect(tela, COR_BOTAO, botao_rect, border_radius=10)
    desenhar_texto(tela, "Jogar Novamente", FONTE_PAINEL_TITULO, COR_TEXTO, botao_rect.center)
    return botao_rect

# --- Telas de Menu ---
def menu_principal(tela): 
    tela.fill(COR_PAINEL)
    desenhar_texto(tela, "Xadrez", FONTE_MENU, COR_TEXTO, (LARGURA_TELA // 2, ALTURA_TELA // 4))
    pvp_rect, pvb_rect = pygame.Rect(LARGURA_TELA // 2 - 200, ALTURA_TELA // 2 - 60, 400, 80), pygame.Rect(LARGURA_TELA // 2 - 200, ALTURA_TELA // 2 + 40, 400, 80)
    pygame.draw.rect(tela, COR_BOTAO, pvp_rect, border_radius=10)
    pygame.draw.rect(tela, COR_BOTAO, pvb_rect, border_radius=10)
    desenhar_texto(tela, "Jogador vs Jogador", FONTE_PAINEL_TITULO, COR_TEXTO, pvp_rect.center)
    desenhar_texto(tela, "Jogador vs Bot", FONTE_PAINEL_TITULO, COR_TEXTO, pvb_rect.center)
    return pvp_rect, pvb_rect

def menu_dificuldade(tela): 
    tela.fill(COR_PAINEL)
    desenhar_texto(tela, "Escolha a Dificuldade", FONTE_MENU, COR_TEXTO, (LARGURA_TELA // 2, ALTURA_TELA // 4))
    facil_rect, medio_rect, dificil_rect = pygame.Rect(LARGURA_TELA // 2 - 150, ALTURA_TELA // 2 - 100, 300, 60), pygame.Rect(LARGURA_TELA // 2 - 150, ALTURA_TELA // 2, 300, 60), pygame.Rect(LARGURA_TELA // 2 - 150, ALTURA_TELA // 2 + 100, 300, 60)
    pygame.draw.rect(tela, COR_BOTAO, facil_rect, border_radius=10), pygame.draw.rect(tela, COR_BOTAO, medio_rect, border_radius=10), pygame.draw.rect(tela, COR_BOTAO, dificil_rect, border_radius=10)
    desenhar_texto(tela, "Bagre (Fácil)", FONTE_PAINEL_TEXTO, COR_TEXTO, facil_rect.center), desenhar_texto(tela, "Joi (Médio)", FONTE_PAINEL_TEXTO, COR_TEXTO, medio_rect.center), desenhar_texto(tela, "Mr Chess (Difícil)", FONTE_PAINEL_TEXTO, COR_TEXTO, dificil_rect.center)
    return facil_rect, medio_rect, dificil_rect

def menu_selecao_cor(tela): 
    tela.fill(COR_PAINEL)
    desenhar_texto(tela, "Escolha sua cor", FONTE_MENU, COR_TEXTO, (LARGURA_TELA // 2, ALTURA_TELA // 4))
    brancas_rect, pretas_rect = pygame.Rect(LARGURA_TELA // 2 - 200, ALTURA_TELA // 2, 180, 80), pygame.Rect(LARGURA_TELA // 2 + 20, ALTURA_TELA // 2, 180, 80)
    pygame.draw.rect(tela, COR_BOTAO, brancas_rect, border_radius=10), pygame.draw.rect(tela, COR_BOTAO, pretas_rect, border_radius=10)
    desenhar_texto(tela, "Brancas", FONTE_PAINEL_TITULO, COR_TEXTO, brancas_rect.center), desenhar_texto(tela, "Pretas", FONTE_PAINEL_TITULO, COR_TEXTO, pretas_rect.center)
    return brancas_rect, pretas_rect

def menu_selecao_tempo(tela):
    tela.fill(COR_PAINEL)
    desenhar_texto(tela, "Controle de Tempo", FONTE_MENU, COR_TEXTO, (LARGURA_TELA // 2, 100))
    opcoes = {"1 min": 60, "5 min": 300, "10 min": 600, "Sem Tempo": None}
    botoes = {}
    y_pos = 200
    for texto, tempo in opcoes.items():
        rect = pygame.Rect(LARGURA_TELA // 2 - 150, y_pos, 300, 60)
        pygame.draw.rect(tela, COR_BOTAO, rect, border_radius=10)
        desenhar_texto(tela, texto, FONTE_PAINEL_TITULO, COR_TEXTO, rect.center)
        botoes[texto] = (rect, tempo)
        y_pos += 80
    return botoes

# --- Função Principal ---
def main():
    if not os.path.exists(NOME_EXECUTAVEL_STOCKFISH):
        print(f"ERRO: Executável do Stockfish não encontrado em '{NOME_EXECUTAVEL_STOCKFISH}'"), sys.exit()

    # Verifica se as imagens existem
    for img_file in ["bagre.jpeg", "joi.jpeg", "mr_chess.jpg", "jogador.jpeg"]:
        if not os.path.exists(os.path.join(CAMINHO_IMAGENS, img_file)):
            print(f"ERRO: Imagem '{img_file}' não encontrada em '{CAMINHO_IMAGENS}'. Certifique-se de ter a pasta 'imagens' com todos os arquivos.")
            sys.exit()

    tela, clock = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA)), pygame.time.Clock()
    pygame.display.set_caption("Xadrez Completo")
    
    # Variáveis de estado
    estado_jogo, modo_jogo, stockfish = "MENU_PRINCIPAL", None, None
    cor_jogador, tabuleiro_invertido, resultado_final = None, False, ""
    skill_bot_atual = None # Para saber qual imagem do bot usar

    # Variáveis da partida
    board = chess.Board()
    quadrado_selecionado, cliques_jogador = None, []
    tempo_brancas, tempo_pretas, tempo_inicial, ultimo_update_relogio = None, None, 0, 0
    
    while True:
        if estado_jogo == "MENU_PRINCIPAL":
            tabuleiro_invertido, modo_jogo, cor_jogador, skill_bot_atual = False, None, None, None # Reset
            pvp_botao, pvb_botao = menu_principal(tela)
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(), sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if pvp_botao.collidepoint(event.pos): modo_jogo, estado_jogo = "pvp", "MENU_TEMPO"
                    elif pvb_botao.collidepoint(event.pos): estado_jogo = "MENU_DIFICULDADE"
                        
        elif estado_jogo == "MENU_DIFICULDADE":
            facil_b, medio_b, dificil_b = menu_dificuldade(tela)
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(), sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    skill = None
                    if facil_b.collidepoint(event.pos): skill, skill_bot_atual = 0, 0
                    elif medio_b.collidepoint(event.pos): skill, skill_bot_atual = 3, 3
                    elif dificil_b.collidepoint(event.pos): skill, skill_bot_atual = 7, 7
                    if skill is not None:
                        stockfish = Stockfish(path=NOME_EXECUTAVEL_STOCKFISH, parameters={"Skill Level": skill})
                        modo_jogo, estado_jogo = "pvb", "MENU_COR"
                        
        elif estado_jogo == "MENU_COR":
            brancas_b, pretas_b = menu_selecao_cor(tela)
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(), sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if brancas_b.collidepoint(event.pos): cor_jogador, tabuleiro_invertido = chess.WHITE, False
                    elif pretas_b.collidepoint(event.pos): cor_jogador, tabuleiro_invertido = chess.BLACK, True
                    if cor_jogador is not None: estado_jogo = "MENU_TEMPO"

        elif estado_jogo == "MENU_TEMPO":
            botoes_tempo = menu_selecao_tempo(tela)
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(), sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    for texto, (rect, tempo) in botoes_tempo.items():
                        if rect.collidepoint(event.pos):
                            tempo_inicial = tempo
                            tempo_brancas, tempo_pretas = tempo, tempo
                            ultimo_update_relogio = pygame.time.get_ticks()
                            board.reset()
                            estado_jogo = "JOGANDO"

        elif estado_jogo == "JOGANDO":
            # Atualização do Relógio
            if tempo_inicial is not None: # Apenas se houver tempo definido
                tempo_atual = pygame.time.get_ticks()
                delta_ms = tempo_atual - ultimo_update_relogio
                ultimo_update_relogio = tempo_atual
                
                if board.turn == chess.WHITE: tempo_brancas -= delta_ms / 1000
                else: tempo_pretas -= delta_ms / 1000
                
                if tempo_brancas is not None and tempo_brancas <= 0:
                    resultado_final = "Pretas venceram no tempo!"
                    estado_jogo = "FIM_DE_JOGO"
                elif tempo_pretas is not None and tempo_pretas <= 0:
                    resultado_final = "Brancas venceram no tempo!"
                    estado_jogo = "FIM_DE_JOGO"

            is_vez_do_bot = modo_jogo == 'pvb' and board.turn != cor_jogador
            if is_vez_do_bot and not board.is_game_over():
                stockfish.set_fen_position(board.fen())
                melhor_jogada = stockfish.get_best_move()
                if melhor_jogada: board.push(chess.Move.from_uci(melhor_jogada))
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(), sys.exit()
                is_vez_do_jogador = (modo_jogo == 'pvp') or (modo_jogo == 'pvb' and board.turn == cor_jogador)
                
                if event.type == pygame.MOUSEBUTTONDOWN and is_vez_do_jogador:
                    pos = event.pos
                    desistir_rect = pygame.Rect(LARGURA_TABULEIRO + 20, ALTURA_TELA - 60, LARGURA_PAINEL - 40, 40) # Recria o rect para o clique
                    if desistir_rect.collidepoint(pos):
                        vencedor = "Pretas" if board.turn == chess.WHITE else "Brancas"
                        resultado_final, estado_jogo = f"{vencedor} venceram por desistência.", "FIM_DE_JOGO"
                        continue
                    if pos[0] > LARGURA_TABULEIRO: continue
                    tela_c, tela_r = pos[0] // TAMANHO_QUADRADO, pos[1] // TAMANHO_QUADRADO
                    if tabuleiro_invertido: quadrado_clicado = chess.square(7 - tela_c, tela_r)
                    else: quadrado_clicado = chess.square(tela_c, 7 - tela_r)
                    if not cliques_jogador:
                        if board.piece_at(quadrado_clicado) and board.color_at(quadrado_clicado) == board.turn:
                            quadrado_selecionado, cliques_jogador = quadrado_clicado, [quadrado_clicado]
                    else:
                        movimento = chess.Move(cliques_jogador[0], quadrado_clicado)
                        if board.piece_type_at(cliques_jogador[0]) == chess.PAWN and chess.square_rank(quadrado_clicado) in [0, 7]:
                            movimento.promotion = chess.QUEEN
                        if movimento in board.legal_moves: board.push(movimento)
                        quadrado_selecionado, cliques_jogador = None, []

            # Geração do histórico
            temp_board, historico_san = chess.Board(), []
            for i, move in enumerate(board.move_stack):
                if i % 2 == 0: historico_san.append(f"{i//2 + 1}. {temp_board.san(move)}")
                else: historico_san[-1] += f" {temp_board.san(move)}"
                temp_board.push(move)
            
            # Desenho
            desenhar_tabuleiro(tela, tabuleiro_invertido)
            desenhar_destaques(tela, board, quadrado_selecionado, board.peek() if board.move_stack else None, tabuleiro_invertido)
            desenhar_pecas(tela, board, tabuleiro_invertido)
            # Passa skill_bot_atual e cor_jogador para a função de desenho
            desistir_rect = desenhar_painel_info(tela, board, tempo_brancas, tempo_pretas, historico_san[-10:], modo_jogo, skill_bot_atual, cor_jogador) 
            pygame.display.flip()

            if board.is_game_over():
                if board.is_checkmate(): resultado_final = f"Xeque-mate! {'Pretas' if board.turn == chess.WHITE else 'Brancas'} venceram."
                else: resultado_final = "Empate!"
                estado_jogo = "FIM_DE_JOGO"

        elif estado_jogo == "FIM_DE_JOGO":
            # Geração do histórico final
            temp_board, historico_san = chess.Board(), []
            for i, move in enumerate(board.move_stack):
                if i % 2 == 0: historico_san.append(f"{i//2 + 1}. {temp_board.san(move)}")
                else: historico_san[-1] += f" {temp_board.san(move)}"
                temp_board.push(move)

            desenhar_tabuleiro(tela, tabuleiro_invertido)
            desenhar_destaques(tela, board, None, board.peek() if board.move_stack else None, tabuleiro_invertido)
            desenhar_pecas(tela, board, tabuleiro_invertido)
            desenhar_painel_info(tela, board, tempo_brancas, tempo_pretas, historico_san[-10:], modo_jogo, skill_bot_atual, cor_jogador)
            botao_reset = desenhar_tela_fim_de_jogo(tela, resultado_final)
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(), sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN and botao_reset.collidepoint(event.pos):
                    estado_jogo = "MENU_PRINCIPAL"
        
        clock.tick(30) # Limita o FPS

if __name__ == '__main__':
    main()