import os
import sys
import pygame
import chess
import math
import time

# dimensões e constantes
LARGURA_TELA, ALTURA_TELA = 1024, 768
LARGURA_TABULEIRO = 640
ALTURA_TABULEIRO = 640
DIMENSAO = 8
TAMANHO_QUADRADO = LARGURA_TABULEIRO // DIMENSAO
LARGURA_PAINEL = LARGURA_TELA - LARGURA_TABULEIRO

# cores
COR_FUNDO = (6, 8, 18)
COR_NEON_PRIMARIA = (0, 255, 255)    # ciano
COR_NEON_SECUNDARIA = (255, 0, 255)  # magenta
COR_SELECAO = (255, 255, 80, 120)
COR_GLOW_VALIDO = (0, 255, 180, 100)
COR_TEXTO = (220, 240, 255)
COR_BOTAO_BG = (18, 18, 30, 180)
COR_RELOGIO_ATIVO = (0, 255, 180)
COR_BOTAO_DESISTIR = (180, 60, 60)

# cores do tabuleiro (semi-translúcidas)
COR_TAB_CLARA = (0, 255, 255, 30)
COR_TAB_ESCURA = (255, 0, 255, 30)

# unicode peças
PECAS_UNICODE = { 'P': '♙', 'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔',
                  'p': '♟', 'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚' }

class UIRenderer:
    def __init__(self, screen, caminho_imagens="imagens", caminho_sons=os.path.join("assets", "sounds")):
        self.screen = screen
        pygame.font.init()

        fonte_padrao = pygame.font.match_font('arial') or pygame.font.get_default_font()
        self.font_pecas = pygame.font.SysFont("Segoe UI Symbol", int(TAMANHO_QUADRADO * 0.8))
        self.font_painel_titulo = pygame.font.Font(fonte_padrao, 28)
        self.font_painel_texto = pygame.font.Font(fonte_padrao, 20)
        self.font_coordenadas = pygame.font.SysFont("helvetica", 14)
        self.font_menu = pygame.font.Font(fonte_padrao, 56)
        self.font_relogio = pygame.font.Font(fonte_padrao, 36)
        self.font_label = pygame.font.Font(fonte_padrao, 18)

        # assets
        self.caminho_imagens = caminho_imagens
        self.caminho_sons = caminho_sons
        self.avatar_tamanho = (80,80)
        self.imagens_bot = {}
        self.imagem_jogador = None
        self.load_images()
        self.load_sounds()

        # precache surfaces para destaque
        self.s_sel = pygame.Surface((TAMANHO_QUADRADO, TAMANHO_QUADRADO), pygame.SRCALPHA)
        self.s_sel.fill(COR_SELECAO)

        self.s_last = pygame.Surface((TAMANHO_QUADRADO, TAMANHO_QUADRADO), pygame.SRCALPHA)
        self.s_last.fill((255, 255, 0, 60))

        self.s_valid = pygame.Surface((TAMANHO_QUADRADO, TAMANHO_QUADRADO), pygame.SRCALPHA)
        self.s_valid.fill(COR_GLOW_VALIDO)

        # menus: rects usados para detecção de clique (centralizados conforme 1024x768)
        self.pvp_rect = pygame.Rect( LARGURA_TELA//2 - 200, ALTURA_TELA//2 - 80, 400, 80)
        self.pvb_rect = pygame.Rect( LARGURA_TELA//2 - 200, ALTURA_TELA//2 + 20, 400, 80)

        self.fácil_rect = pygame.Rect(LARGURA_TELA//2 - 150, ALTURA_TELA//2 - 100, 300, 60)
        self.medio_rect = pygame.Rect(LARGURA_TELA//2 - 150, ALTURA_TELA//2, 300, 60)
        self.dificil_rect = pygame.Rect(LARGURA_TELA//2 - 150, ALTURA_TELA//2 + 100, 300, 60)

        self.br_rect = pygame.Rect(LARGURA_TELA//2 - 200, ALTURA_TELA//2, 180,80)
        self.pr_rect = pygame.Rect(LARGURA_TELA//2 + 20, ALTURA_TELA//2, 180,80)

        # botões tempo
        self.t_botoes = {}
        y = 220
        for txt in ["1 min","5 min","10 min","Sem Tempo"]:
            rect = pygame.Rect(LARGURA_TELA//2 - 150, y, 300, 60)
            self.t_botoes[txt] = rect
            y += 80

        # estados auxiliares para a UI do tabuleiro
        self.promotion_pending = False
        self.promotion_choices = []  # lista de tuples (rect, piece_type)
        self.promotion_color_is_white = True

        # plano de fundo animado (podemos redesenhar cada frame)
        self.bg_surface = pygame.Surface((LARGURA_TELA, ALTURA_TELA))

    # ---------------- carregamento de assets ----------------
    def load_images(self):
        files = {"bagre":"bagre.jpeg","joi":"joi.jpeg","mr":"mr_chess.jpg","jogador":"jogador.jpeg"}
        for k, fname in files.items():
            path = os.path.join(self.caminho_imagens, fname)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    img = pygame.transform.scale(img, self.avatar_tamanho)
                    if k == "jogador":
                        self.imagem_jogador = img
                    else:
                        key = "Bagre" if "bagre" in fname else ("Joi" if "joi" in fname else "Mr Chess")
                        self.imagens_bot[key] = img
                except Exception as e:
                    print("Erro carregando imagem:", path, e)
            else:
                # não achar é normal em máquinas diferentes
                #print("Imagem não encontrada:", path)
                pass
        # placeholder se não existirem
        if self.imagem_jogador is None:
            surf = pygame.Surface(self.avatar_tamanho)
            surf.fill((200,200,200))
            self.imagem_jogador = surf

    def load_sounds(self):
        try:
            pygame.mixer.init()
            self.sons = {}
            for name in ["move","capture","check"]:
                path = os.path.join(self.caminho_sons, f"{name}.wav")
                if os.path.exists(path):
                    self.sons[name] = pygame.mixer.Sound(path)
        except Exception as e:
            print("Erro inicializando mixer/sounds:", e)
            self.sons = {}

    def play_sound(self, nome):
        try:
            if nome in self.sons:
                self.sons[nome].play()
        except Exception as e:
            print("Erro ao tocar som:", e)

    def play_sound_for_move(self, board, move):
        # chamar sempre 'move'; 'check' se estiver em cheque
        self.play_sound('move')
        if board.is_check():
            self.play_sound('check')


    # ------------------ utilitário: desenhar fundo animado ------------------
    def _draw_background_animation(self):
        # fundo escuro
        self.bg_surface.fill(COR_FUNDO)

        # linhas horizontais e linhas finas neon com opacidade dinâmica
        t = time.time()
        for i in range(0, ALTURA_TELA, 40):
            alpha = int(10 + 20 * (0.5 + 0.5 * math.sin(t + i * 0.01)))
            s = pygame.Surface((LARGURA_TELA, 2), pygame.SRCALPHA)
            s.fill((30, 10, 40, alpha))
            self.bg_surface.blit(s, (0, i))

        # um gradiente sutil vertical (cima mais escuro)
        grad = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        for y in range(ALTURA_TELA):
            v = int(8 + 40 * (y / ALTURA_TELA))
            grad.fill((v, 6, 20, 8), rect=pygame.Rect(0, y, LARGURA_TELA, 1))
        self.bg_surface.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # efeitos de nuvem/neon (círculos translúcidos)
        for i in range(6):
            cx = int((LARGURA_TELA * (i + 1) / 7) + 80 * math.sin(t * 0.3 + i))
            cy = int(120 * math.sin(t * 0.7 + i) + 120 + i * 40)
            r = 220
            s = pygame.Surface((r, r), pygame.SRCALPHA)
            alpha_val = max(0, min(255, int(8 + 20 * math.sin(t + i))))
            color = (
                int(COR_NEON_PRIMARIA[0]),
                int(COR_NEON_PRIMARIA[1]),
                int(COR_NEON_PRIMARIA[2]),
                alpha_val
            )
            pygame.draw.circle(s, color, (r//2, r//2), r//2)
            self.bg_surface.blit(s, (cx - r//2, cy - r//2), special_flags=pygame.BLEND_RGBA_ADD)

        self.screen.blit(self.bg_surface, (0, 0))

    # ------------------ BOTÕES NEON ------------------
    def _draw_neon_button(self, rect: pygame.Rect, texto: str):
        # animação pulsante
        glow = 150 + int(80 * (0.5 + 0.5 * math.sin(time.time() * 2)))
        cor_borda = (min(255, glow), 0, 255)
        # fundo translúcido
        s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        s.fill(COR_BOTAO_BG)
        self.screen.blit(s, rect.topleft)
        # borda neon
        pygame.draw.rect(self.screen, cor_borda, rect, width=3, border_radius=14)
        # texto central
        self.draw_text_center(texto, self.font_painel_titulo, COR_TEXTO, rect.center)


    # ------------------- Menus (desenho + eventos simples não bloqueantes) -------------------

    def draw_menu_principal(self):
        self._draw_background_animation()
        titulo = self.font_menu.render("Xadrez Por Voz", True, COR_NEON_SECUNDARIA)
        self.screen.blit(titulo, (LARGURA_TELA//2 - titulo.get_width()//2, 120))
        self._draw_neon_button(self.pvp_rect, "Jogador vs Jogador")
        self._draw_neon_button(self.pvb_rect, "Jogador vs Bot")
        return self.pvp_rect, self.pvb_rect

    def handle_menu_principal_event(self, event, pvp_rect, pvb_rect):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if pvp_rect.collidepoint(event.pos):
                return "pvp"
            if pvb_rect.collidepoint(event.pos):
                return "pvb"
        return None

    def draw_menu_dificuldade(self):
        self._draw_background_animation()
        self.draw_text_center("Escolha a dificuldade", self.font_menu, COR_NEON_SECUNDARIA, (LARGURA_TELA//2, 120))
        self._draw_neon_button(self.fácil_rect, "Bagre (Fácil)")
        self._draw_neon_button(self.medio_rect, "Joi (Médio)")
        self._draw_neon_button(self.dificil_rect, "Mr Chess (Difícil)")

    def handle_menu_dificuldade_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.fácil_rect.collidepoint(event.pos):
                return 0  # skill
            if self.medio_rect.collidepoint(event.pos):
                return 3
            if self.dificil_rect.collidepoint(event.pos):
                return 7
        return None

    def draw_menu_cor(self):
        self._draw_background_animation()
        self.draw_text_center("Escolha sua cor", self.font_menu, COR_NEON_SECUNDARIA, (LARGURA_TELA//2, 120))
        self._draw_neon_button(self.br_rect, "Brancas")
        self._draw_neon_button(self.pr_rect, "Pretas")

    def handle_menu_cor_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.br_rect.collidepoint(event.pos):
                return chess.WHITE
            if self.pr_rect.collidepoint(event.pos):
                return chess.BLACK
        return None

    def draw_menu_tempo(self):
        self._draw_background_animation()
        self.draw_text_center("Controle de Tempo", self.font_menu, COR_NEON_SECUNDARIA, (LARGURA_TELA//2, 100))
        for txt, rect in self.t_botoes.items():
            self._draw_neon_button(rect, txt)
        return self.t_botoes

    def handle_menu_tempo_event(self, event, botoes):
        if event.type == pygame.MOUSEBUTTONDOWN:
            for txt, rect in botoes.items():
                if rect.collidepoint(event.pos):
                    if txt == "Sem Tempo":
                        return None
                    # mapear "5 min" -> segundos
                    mins = int(txt.split()[0])
                    return mins * 60
        return None

    # ------------------- Desenho do tabuleiro, peças, destaques e painel -------------------

    def draw_board(self, board: chess.Board, tabuleiro_invertido: bool, quadrado_selecionado, ultimo_mov):
        # fundo do tabuleiro
        self._draw_background_animation()

        # desenhar tabuleiro: quadrados translúcidos com bordas neon finas
        for r in range(DIMENSAO):
            for c in range(DIMENSAO):
                rect = pygame.Rect(c * TAMANHO_QUADRADO, r * TAMANHO_QUADRADO, TAMANHO_QUADRADO, TAMANHO_QUADRADO)
                cor_trans = COR_TAB_CLARA if (r + c) % 2 == 0 else COR_TAB_ESCURA
                s = pygame.Surface((TAMANHO_QUADRADO, TAMANHO_QUADRADO), pygame.SRCALPHA)
                s.fill(cor_trans)
                self.screen.blit(s, (rect.x, rect.y))
                borda_cor = COR_NEON_PRIMARIA if (r + c) % 2 == 0 else COR_NEON_SECUNDARIA
                pygame.draw.rect(self.screen, borda_cor, rect, width=1)

                # coordenadas pequenas (agora em todos os quadrados no formato coluna-linha: "col-row", com 1-1 no canto inferior-esquerdo)
                col_index = c + 1  # coluna da esquerda para a direita, começando em 1
                row_index = DIMENSAO - r  # linhas de baixo para cima, 1 na linha inferior
                label = f"{col_index}-{row_index}"
                small = self.font_label.render(label, True, (90, 90, 110))
                # posicionar no canto inferior-esquerdo do quadrado
                self.screen.blit(small, (rect.x + 2, rect.y + TAMANHO_QUADRADO - small.get_height() - 2))

        # último movimento
        if ultimo_mov:
            for q in [ultimo_mov.from_square, ultimo_mov.to_square]:
                r, c = self.get_pos_tela(q, tabuleiro_invertido)
                self.screen.blit(self.s_last, (c * TAMANHO_QUADRADO, r * TAMANHO_QUADRADO))

        # seleção e movimentos válidos
        if quadrado_selecionado is not None:
            r, c = self.get_pos_tela(quadrado_selecionado, tabuleiro_invertido)
            self.screen.blit(self.s_sel, (c * TAMANHO_QUADRADO, r * TAMANHO_QUADRADO))
            for mv in board.legal_moves:
                if mv.from_square == quadrado_selecionado:
                    r2, c2 = self.get_pos_tela(mv.to_square, tabuleiro_invertido)
                    center = (c2 * TAMANHO_QUADRADO + TAMANHO_QUADRADO // 2, r2 * TAMANHO_QUADRADO + TAMANHO_QUADRADO // 2)
                    pygame.draw.circle(self.screen, COR_NEON_PRIMARIA, center, 10)

        # desenhar peças (unicode) com leve offset/float
        for i in range(64):
            p = board.piece_at(i)
            if not p:
                continue
            rank_real, file_real = chess.square_rank(i), chess.square_file(i)
            if tabuleiro_invertido:
                r, c = rank_real, 7 - file_real
            else:
                r, c = 7 - rank_real, file_real
            simbolo = PECAS_UNICODE[p.symbol()]
            cor_peca = pygame.Color('black') if p.color == chess.BLACK else pygame.Color('white')
            sombra = self.font_pecas.render(simbolo, True, (10, 10, 10))
            texto = self.font_pecas.render(simbolo, True, cor_peca)
            pos_x = c * TAMANHO_QUADRADO + (TAMANHO_QUADRADO - texto.get_width()) // 2
            pos_y = r * TAMANHO_QUADRADO + (TAMANHO_QUADRADO - texto.get_height()) // 2
            offset = int(2 * math.sin(time.time() * 3 + i))
            # shadow
            self.screen.blit(sombra, (pos_x + 2, pos_y + 2 + offset))
            # piece
            self.screen.blit(texto, (pos_x, pos_y + offset))

        # se há promoção pendente, desenhar modal de promoção (não bloqueante)
        if self.promotion_pending:
            self._draw_promotion_modal()

    # ------------------ PAINEL LATERAL ------------------
    def draw_panel_info(self, board, tempo_brancas, tempo_pretas, historico_san, modo_jogo, skill_bot, cor_jogador):
        # painel semi-transparente
        painel_rect = pygame.Rect(LARGURA_TABULEIRO, 0, LARGURA_PAINEL, ALTURA_TELA)
        s = pygame.Surface((painel_rect.w, painel_rect.h), pygame.SRCALPHA)
        s.fill((6, 8, 18, 220))
        self.screen.blit(s, painel_rect.topleft)

        centro_x = LARGURA_TABULEIRO + LARGURA_PAINEL // 2
        y = 20

        self.draw_text_center("Adversário", self.font_label, COR_TEXTO, (centro_x, y))
        y += 40

        avatar = None
        if modo_jogo == "pvp":
            avatar = self.imagem_jogador
        elif modo_jogo == "pvb":
            if skill_bot == 0: avatar = self.imagens_bot.get("Bagre")
            elif skill_bot == 3: avatar = self.imagens_bot.get("Joi")
            elif skill_bot == 7: avatar = self.imagens_bot.get("Mr Chess")
        if avatar:
            ar = avatar.get_rect(center=(centro_x, y + self.avatar_tamanho[1]//2))
            self.screen.blit(avatar, ar)
            y = ar.bottom + 10

        # relógio adversário (top)
        cor_rel = COR_RELOGIO_ATIVO if board.turn != cor_jogador else (70, 70, 80)
        rect_rel = pygame.Rect(LARGURA_TABULEIRO + 10, y, LARGURA_PAINEL - 20, 45)
        pygame.draw.rect(self.screen, cor_rel, rect_rel, border_radius=10)
        tempo_op = tempo_pretas if cor_jogador == chess.WHITE else tempo_brancas
        self.draw_text_center(self.format_time(tempo_op), self.font_relogio, COR_TEXTO, rect_rel.center)
        y = rect_rel.bottom + 20

        # histórico
        self.draw_text_center("Histórico", self.font_painel_texto, COR_TEXTO, (centro_x, y))
        y += 30
        for i, txt in enumerate(historico_san[-12:]):
            if y + i*22 < ALTURA_TELA - 160:
                self.draw_text_center(txt, self.font_painel_texto, COR_TEXTO, (centro_x, y + i*22))

        # inferior: botão desistir, relógio jogador e avatar jogador
        y_inf = ALTURA_TELA - 30
        desistir_rect = pygame.Rect(LARGURA_TABULEIRO + 20, y_inf - 50, LARGURA_PAINEL - 40, 40)
        # desenhar botão neon (pequeno)
        self._draw_neon_button(desistir_rect, "Desistir")
        y_inf = desistir_rect.top - 10

        cor_rel_j = COR_RELOGIO_ATIVO if board.turn == cor_jogador else (70, 70, 80)
        rect_rel_j = pygame.Rect(LARGURA_TABULEIRO + 10, y_inf - 45, LARGURA_PAINEL - 20, 45)
        pygame.draw.rect(self.screen, cor_rel_j, rect_rel_j, border_radius=10)
        tempo_j = tempo_brancas if cor_jogador == chess.WHITE or modo_jogo == "pvp" else tempo_pretas
        self.draw_text_center(self.format_time(tempo_j), self.font_relogio, COR_TEXTO, rect_rel_j.center)

        avatar_j_rect = self.imagem_jogador.get_rect(center=(centro_x, rect_rel_j.top - self.avatar_tamanho[1]//2 - 5))
        self.screen.blit(self.imagem_jogador, avatar_j_rect)
        self.draw_text_center("Jogador", self.font_label, COR_TEXTO, (centro_x, avatar_j_rect.top - 15))

        return desistir_rect

    # ------------------ TELA DE FIM ------------------
    def draw_end_screen(self, resultado):
        s = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (0, 0))
        self.draw_text_center(resultado, self.font_menu, (255, 215, 0), (LARGURA_TELA//2, ALTURA_TELA//3))
        bot_rect = pygame.Rect(LARGURA_TELA//2 - 150, ALTURA_TELA//2, 300, 80)
        self._draw_neon_button(bot_rect, "Jogar Novamente")
        return bot_rect
    
    # ------------------- Promoção (não bloqueante) -------------------

    def start_promotion(self, color_white=True):
        # prepara modal de promoção
        self.promotion_pending = True
        self.promotion_choices = []
        self.promotion_color_is_white = color_white
        labels = ["Dama","Torre","Bispo","Cavalo"]
        types = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        width = 120
        total_w = width * len(types) + 20*(len(types)-1)
        x0 = LARGURA_TELA//2 - total_w//2
        y0 = ALTURA_TELA//2 - 40
        for i, t in enumerate(types):
            r = pygame.Rect(x0 + i*(width+20), y0, width, 80)
            self.promotion_choices.append((r, t, labels[i]))

    def _draw_promotion_modal(self):
        overlay = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        for r, t, lab in self.promotion_choices:
            pygame.draw.rect(self.screen, (20, 20, 30), r, border_radius=8)
            pygame.draw.rect(self.screen, COR_NEON_PRIMARIA, r, width=2, border_radius=8)
            self.draw_text_center(lab, self.font_painel_texto, COR_TEXTO, r.center)

    def end_promotion(self):
        self.promotion_pending = False
        self.promotion_choices = []

    # ------------------- Eventos do jogo (cliques no tabuleiro etc.) -------------------

    def handle_jogo_event(self, event, state, tabuleiro_invertido, cor_jogador, modo_jogo):
        """
        Recebe events do main loop e retorna:
          - chess.Move (quando jogador completou movimento)
          - "DESISTIR" (quando clicou desistir)
          - None (nada a fazer)
        Ele também trata a modal de promoção de forma não-bloqueante.
        """
        # se promoção pendente: apenas capturar clique nas opções
        if self.promotion_pending and event.type == pygame.MOUSEBUTTONDOWN:
            for rect, piece_type, _ in self.promotion_choices:
                if rect.collidepoint(event.pos):
                    # construir move com promoção guardada no state
                    from_sq = state.pending_promotion['from']
                    to_sq = state.pending_promotion['to']
                    mv = chess.Move(from_sq, to_sq, promotion=piece_type)
                    self.end_promotion()
                    state.pending_promotion = None
                    return mv
            return None

        # detectar clique em painel (desistir)
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos
            # botão desistir (coordenadas no painel)
            desistir_rect = pygame.Rect(LARGURA_TABULEIRO + 20, ALTURA_TELA - 80, LARGURA_PAINEL - 40, 40)
            if desistir_rect.collidepoint(pos):
                return "DESISTIR"

            # clique no tabuleiro (área esquerda)
            if pos[0] <= LARGURA_TABULEIRO and pos[1] <= ALTURA_TABULEIRO:
                tela_c, tela_r = pos[0] // (TAMANHO_QUADRADO), pos[1] // (TAMANHO_QUADRADO)
                if tabuleiro_invertido:
                    quadrado = chess.square(7 - tela_c, tela_r)
                else:
                    quadrado = chess.square(tela_c, 7 - tela_r)

                # seleção / movimento
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
                        # promoção: se for peão e chegar na última file
                        if state.board.piece_type_at(state.cliques_jogador[0]) == chess.PAWN and chess.square_rank(quadrado) in [0,7]:
                            # começar promoção não bloqueante
                            state.pending_promotion = {'from': state.cliques_jogador[0], 'to': quadrado}
                            self.start_promotion(color_white=(state.board.turn == chess.WHITE))
                            # limpar seleção (aguardar escolha)
                            state.quadrado_selecionado = None
                            state.cliques_jogador = []
                            return None
                        # jogada normal
                        if mv in state.board.legal_moves:
                            # reset seleção e retornar a jogada para main aplicar
                            state.quadrado_selecionado = None
                            state.cliques_jogador = []
                            return mv
                        else:
                            # jogada ilegal: limpar seleção
                            state.quadrado_selecionado = None
                            state.cliques_jogador = []
        return None

    def handle_fim_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # qualquer clique reinicia
            return "REINICIAR"
        return None

    # ------------------- utilitários -------------------

    def draw_text_center(self, texto, fonte, cor, centro):
        obj = fonte.render(texto, True, cor)
        rect = obj.get_rect(center=centro)
        self.screen.blit(obj, rect)

    def format_time(self, segundos):
        if segundos is None: return "--:--"
        if segundos <= 0: return "00:00"
        minutos = math.floor(segundos/60)
        segs = math.floor(segundos%60)
        return f"{minutos:02d}:{segs:02d}"

    def get_pos_tela(self, quadrado, tabuleiro_invertido):
        rank, file = chess.square_rank(quadrado), chess.square_file(quadrado)
        if tabuleiro_invertido:
            return rank, 7 - file
        else:
            return 7 - rank, file
