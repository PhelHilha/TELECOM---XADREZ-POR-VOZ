# ui_renderer.py
import os
import pygame
import chess
import math

# constantes visuais (compatíveis com o seu design anterior)
LARGURA_TELA, ALTURA_TELA = 880, 640
LARGURA_TABULEIRO, ALTURA_TABULEIRO = 640, 640
DIMENSAO = 8
TAMANHO_QUADRADO = LARGURA_TABULEIRO // DIMENSAO
LARGURA_PAINEL = LARGURA_TELA - LARGURA_TABULEIRO

COR_CLARA = pygame.Color(238, 238, 210)
COR_ESCURA = pygame.Color(118, 150, 86)
COR_DESTAQUE_SELECAO = pygame.Color(255, 255, 51, 160)
COR_DESTAQUE_ULTIMO_MOV = pygame.Color(170, 162, 58, 150)
COR_DESTAQUE_VALIDO = pygame.Color(0, 0, 0, 80)
COR_PAINEL = pygame.Color("gray20")
COR_TEXTO = pygame.Color("white")
COR_BOTAO = pygame.Color("gray30")
COR_BOTAO_DESISTIR = pygame.Color(180, 60, 60)
COR_RELOGIO_ATIVO = pygame.Color(120, 190, 120)

PECAS_UNICODE = { 'P': '♙', 'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔',
                  'p': '♟', 'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚' }

class UIRenderer:
    def __init__(self, screen, caminho_imagens="imagens", caminho_sons=os.path.join("assets","sounds")):
        self.screen = screen
        pygame.font.init()
        self.font_pecas = pygame.font.SysFont("Segoe UI Symbol", int(TAMANHO_QUADRADO * 0.8))
        self.font_painel_titulo = pygame.font.SysFont("helvetica", 32)
        self.font_painel_texto = pygame.font.SysFont("helvetica", 24)
        self.font_coordenadas = pygame.font.SysFont("helvetica", 16)
        self.font_menu = pygame.font.SysFont("helvetica", 50)
        self.font_relogio = pygame.font.SysFont("monospace", 40, bold=True)
        self.font_label = pygame.font.SysFont("helvetica", 20, bold=True)

        self.caminho_imagens = caminho_imagens
        self.caminho_sons = caminho_sons
        self.avatar_tamanho = (80,80)
        self.imagens_bot = {}
        self.imagem_jogador = None
        self.load_images()
        self.load_sounds()

        # precache surfaces
        self.s_sel = pygame.Surface((TAMANHO_QUADRADO, TAMANHO_QUADRADO), pygame.SRCALPHA)
        self.s_sel.fill(COR_DESTAQUE_SELECAO)
        self.s_last = pygame.Surface((TAMANHO_QUADRADO, TAMANHO_QUADRADO), pygame.SRCALPHA)
        self.s_last.fill(COR_DESTAQUE_ULTIMO_MOV)

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
                print("Imagem não encontrada:", path)
        # placeholder se não existirem
        if self.imagem_jogador is None:
            surf = pygame.Surface(self.avatar_tamanho)
            surf.fill((200,200,200))
            self.imagem_jogador = surf

    def load_sounds(self):
        pygame.mixer.init()
        self.sons = {}
        try:
            for name in ["move","capture","check"]:
                path = os.path.join(self.caminho_sons, f"{name}.wav")
                if os.path.exists(path):
                    self.sons[name] = pygame.mixer.Sound(path)
                else:
                    print("Som não encontrado:", path)
        except Exception as e:
            print("Erro inicializando mixer/sounds:", e)

    def play_sound(self, nome):
        try:
            if nome in self.sons:
                self.sons[nome].play()
        except Exception as e:
            print("Erro ao tocar som:", e)

    def play_sound_for_move(self, board, move):
        # tocar move/capture/check
        # move é um objeto chess.Move que já foi aplicado ao board (push já feito)
        # para detectar captura, analisamos se a jogada capturou (board.is_capture não aceita move depois de push), usar board.is_capture(move) antes de push.
        # aqui assumimos que chamaram depois do push, então detectaremos capturas pela diferença de peças.
        # Simples: tocar move sempre, capture se a jogada capturou (checar via .piece_type_at no to_square antes da push não disponível). 
        # Para simplicidade, tocamos 'move' e 'check' se estiver em cheque.
        self.play_sound('move')
        if board.is_check():
            self.play_sound('check')

    # --- Desenho de menus (retornam rects para clique) ---
    def draw_menu_principal(self):
        self.screen.fill(COR_PAINEL)
        titulo = self.font_menu.render("Xadrez", True, COR_TEXTO)
        self.screen.blit(titulo, (LARGURA_TELA//2 - titulo.get_width()//2, ALTURA_TELA//4))
        pvp = pygame.Rect(LARGURA_TELA//2 - 200, ALTURA_TELA//2 - 60, 400,80)
        pvb = pygame.Rect(LARGURA_TELA//2 - 200, ALTURA_TELA//2 + 40, 400,80)
        pygame.draw.rect(self.screen, COR_BOTAO, pvp, border_radius=10)
        pygame.draw.rect(self.screen, COR_BOTAO, pvb, border_radius=10)
        self.draw_text_center("Jogador vs Jogador", self.font_painel_titulo, COR_TEXTO, pvp.center)
        self.draw_text_center("Jogador vs Bot", self.font_painel_titulo, COR_TEXTO, pvb.center)
        return pvp, pvb

    def draw_menu_dificuldade(self):
        self.screen.fill(COR_PAINEL)
        self.draw_text_center("Escolha a Dificuldade", self.font_menu, COR_TEXTO, (LARGURA_TELA//2, ALTURA_TELA//4))
        facil = pygame.Rect(LARGURA_TELA//2 - 150, ALTURA_TELA//2 - 100, 300, 60)
        medio = pygame.Rect(LARGURA_TELA//2 - 150, ALTURA_TELA//2, 300, 60)
        dificil = pygame.Rect(LARGURA_TELA//2 - 150, ALTURA_TELA//2 + 100, 300, 60)
        pygame.draw.rect(self.screen, COR_BOTAO, facil, border_radius=10)
        pygame.draw.rect(self.screen, COR_BOTAO, medio, border_radius=10)
        pygame.draw.rect(self.screen, COR_BOTAO, dificil, border_radius=10)
        self.draw_text_center("Bagre (Fácil)", self.font_painel_texto, COR_TEXTO, facil.center)
        self.draw_text_center("Joi (Médio)", self.font_painel_texto, COR_TEXTO, medio.center)
        self.draw_text_center("Mr Chess (Difícil)", self.font_painel_texto, COR_TEXTO, dificil.center)
        return facil, medio, dificil

    def draw_menu_cor(self):
        self.screen.fill(COR_PAINEL)
        self.draw_text_center("Escolha sua cor", self.font_menu, COR_TEXTO, (LARGURA_TELA//2, ALTURA_TELA//4))
        br = pygame.Rect(LARGURA_TELA//2 - 200, ALTURA_TELA//2, 180,80)
        pr = pygame.Rect(LARGURA_TELA//2 + 20, ALTURA_TELA//2, 180,80)
        pygame.draw.rect(self.screen, COR_BOTAO, br, border_radius=10)
        pygame.draw.rect(self.screen, COR_BOTAO, pr, border_radius=10)
        self.draw_text_center("Brancas", self.font_painel_titulo, COR_TEXTO, br.center)
        self.draw_text_center("Pretas", self.font_painel_titulo, COR_TEXTO, pr.center)
        return br, pr

    def draw_menu_tempo(self):
        self.screen.fill(COR_PAINEL)
        self.draw_text_center("Controle de Tempo", self.font_menu, COR_TEXTO, (LARGURA_TELA//2, 100))
        opcoes = {"1 min": 60, "5 min": 300, "10 min": 600, "Sem Tempo": None}
        botoes = {}
        y = 200
        for txt, t in opcoes.items():
            rect = pygame.Rect(LARGURA_TELA//2 - 150, y, 300, 60)
            pygame.draw.rect(self.screen, COR_BOTAO, rect, border_radius=10)
            self.draw_text_center(txt, self.font_painel_titulo, COR_TEXTO, rect.center)
            botoes[txt] = (rect, t)
            y += 80
        return botoes

    # --- Desenho do tabuleiro, peças, destaques e painel ---
    def draw_board(self, board: chess.Board, tabuleiro_invertido: bool, quadrado_selecionado, ultimo_mov):
        # desenha tabuleiro e coordenadas
        for r in range(DIMENSAO):
            for c in range(DIMENSAO):
                cor = COR_CLARA if (r + c) % 2 == 0 else COR_ESCURA
                pygame.draw.rect(self.screen, cor, pygame.Rect(c * TAMANHO_QUADRADO, r * TAMANHO_QUADRADO, TAMANHO_QUADRADO, TAMANHO_QUADRADO))
                if tabuleiro_invertido:
                    quadrado_real = chess.square(7 - c, r)
                else:
                    quadrado_real = chess.square(c, 7 - r)
                coord = chess.SQUARE_NAMES[quadrado_real]
                txt = self.font_coordenadas.render(coord, True, COR_ESCURA if (r + c) % 2 == 0 else COR_CLARA)
                self.screen.blit(txt, (c * TAMANHO_QUADRADO + 2, r * TAMANHO_QUADRADO + 2))

        # último movimento
        if ultimo_mov:
            for q in [ultimo_mov.from_square, ultimo_mov.to_square]:
                r, c = self.get_pos_tela(q, tabuleiro_invertido)
                self.screen.blit(self.s_last, (c * TAMANHO_QUADRADO, r * TAMANHO_QUADRADO))

        # seleção e movimentos válidos
        if quadrado_selecionado is not None:
            r, c = self.get_pos_tela(quadrado_selecionado, tabuleiro_invertido)
            self.screen.blit(self.s_sel, (c * TAMANHO_QUADRADO, r * TAMANHO_QUADRADO))
            s = pygame.Surface((TAMANHO_QUADRADO, TAMANHO_QUADRADO), pygame.SRCALPHA)
            s.fill(COR_DESTAQUE_VALIDO)
            for mv in board.legal_moves:
                if mv.from_square == quadrado_selecionado:
                    r2, c2 = self.get_pos_tela(mv.to_square, tabuleiro_invertido)
                    center = (c2 * TAMANHO_QUADRADO + TAMANHO_QUADRADO // 2, r2 * TAMANHO_QUADRADO + TAMANHO_QUADRADO // 2)
                    pygame.draw.circle(self.screen, s.get_at((0,0)), center, 12)

        # peças
        for i in range(64):
            p = board.piece_at(i)
            if not p: continue
            rank_real, file_real = chess.square_rank(i), chess.square_file(i)
            if tabuleiro_invertido:
                r, c = rank_real, 7 - file_real
            else:
                r, c = 7 - rank_real, file_real
            simbolo = PECAS_UNICODE[p.symbol()]
            cor_peca = pygame.Color('black') if p.color == chess.BLACK else pygame.Color('white')
            sombra = self.font_pecas.render(simbolo, True, pygame.Color('gray10'))
            texto = self.font_pecas.render(simbolo, True, cor_peca)
            pos_x = c * TAMANHO_QUADRADO + (TAMANHO_QUADRADO - texto.get_width()) // 2
            pos_y = r * TAMANHO_QUADRADO + (TAMANHO_QUADRADO - texto.get_height()) // 2
            for off in [(1,1),(1,-1),(-1,1),(-1,-1)]:
                self.screen.blit(sombra, (pos_x + off[0], pos_y + off[1]))
            self.screen.blit(texto, (pos_x, pos_y))

    def draw_panel_info(self, board, tempo_brancas, tempo_pretas, historico_san, modo_jogo, skill_bot, cor_jogador):
        pygame.draw.rect(self.screen, COR_PAINEL, pygame.Rect(LARGURA_TABULEIRO, 0, LARGURA_PAINEL, ALTURA_TELA))
        centro_x = LARGURA_TABULEIRO + LARGURA_PAINEL // 2
        y = 20
        self.draw_text_center("Adversário", self.font_label, COR_TEXTO, (centro_x, y))
        y += 30

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

        cor_rel = COR_RELOGIO_ATIVO if board.turn != cor_jogador else COR_BOTAO
        rect_rel = pygame.Rect(LARGURA_TABULEIRO + 10, y, LARGURA_PAINEL - 20, 45)
        pygame.draw.rect(self.screen, cor_rel, rect_rel, border_radius=10)
        tempo_op = tempo_pretas if cor_jogador == chess.WHITE else tempo_brancas
        self.draw_text_center(self.format_time(tempo_op), self.font_relogio, COR_TEXTO, rect_rel.center)
        y = rect_rel.bottom + 20

        self.draw_text_center("Histórico", self.font_painel_texto, COR_TEXTO, (centro_x, y))
        y += 25
        for i, txt in enumerate(historico_san[-12:]):
            if y + i*22 < ALTURA_TELA - 140:
                self.draw_text_center(txt, self.font_painel_texto, COR_TEXTO, (centro_x, y + i*22))

        # inferior: botão desistir, relógio e avatar jogador
        y_inf = ALTURA_TELA - 20
        desistir_rect = pygame.Rect(LARGURA_TABULEIRO + 20, y_inf - 40, LARGURA_PAINEL - 40, 40)
        pygame.draw.rect(self.screen, COR_BOTAO_DESISTIR, desistir_rect, border_radius=10)
        self.draw_text_center("Desistir", self.font_painel_texto, COR_TEXTO, desistir_rect.center)
        y_inf = desistir_rect.top - 10

        cor_rel_j = COR_RELOGIO_ATIVO if board.turn == cor_jogador else COR_BOTAO
        rect_rel_j = pygame.Rect(LARGURA_TABULEIRO + 10, y_inf - 45, LARGURA_PAINEL - 20, 45)
        pygame.draw.rect(self.screen, cor_rel_j, rect_rel_j, border_radius=10)
        tempo_j = tempo_brancas if cor_jogador == chess.WHITE or modo_jogo == "pvp" else tempo_pretas
        self.draw_text_center(self.format_time(tempo_j), self.font_relogio, COR_TEXTO, rect_rel_j.center)

        avatar_j_rect = self.imagem_jogador.get_rect(center=(centro_x, rect_rel_j.top - self.avatar_tamanho[1]//2 - 5))
        self.screen.blit(self.imagem_jogador, avatar_j_rect)
        self.draw_text_center("Jogador", self.font_label, COR_TEXTO, (centro_x, avatar_j_rect.top - 15))

        return desistir_rect

    def draw_end_screen(self, resultado):
        s = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        s.fill((0,0,0,180))
        self.screen.blit(s, (0,0))
        self.draw_text_center(resultado, self.font_menu, pygame.Color('gold'), (LARGURA_TELA//2, ALTURA_TELA//3))
        bot_rect = pygame.Rect(LARGURA_TELA//2 - 150, ALTURA_TELA//2, 300, 80)
        pygame.draw.rect(self.screen, COR_BOTAO, bot_rect, border_radius=10)
        self.draw_text_center("Jogar Novamente", self.font_painel_titulo, COR_TEXTO, bot_rect.center)
        return bot_rect

    def promotion_modal(self, cor_brancas: bool):
        choices = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        labels = ["Dama","Torre","Bispo","Cavalo"]
        overlay = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        overlay.fill((0,0,0,180))
        self.screen.blit(overlay, (0,0))
        width = 120
        total_w = width * len(choices) + 20*(len(choices)-1)
        x0 = LARGURA_TELA//2 - total_w//2
        y0 = ALTURA_TELA//2 - 40
        rects = []
        for i, lab in enumerate(labels):
            r = pygame.Rect(x0 + i*(width+20), y0, width, 80)
            pygame.draw.rect(self.screen, COR_BOTAO, r, border_radius=8)
            self.draw_text_center(lab, self.font_painel_texto, COR_TEXTO, r.center)
            rects.append((r, choices[i]))
        pygame.display.flip()
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if e.type == pygame.MOUSEBUTTONDOWN:
                    for r, val in rects:
                        if r.collidepoint(e.pos):
                            return val
            pygame.time.Clock().tick(30)

    # util
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
