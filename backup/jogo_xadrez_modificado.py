# xadrez_completo_v6.py

import os
import sys
import math
import pygame
import chess
from stockfish import Stockfish
from typing import Optional, Tuple, List

# --- CONFIGURAÇÕES ---
NOME_EXECUTAVEL_STOCKFISH = "stockfish.exe"
CAMINHO_IMAGENS = "imagens"

# --- CONSTANTES ---
LARGURA_TELA, ALTURA_TELA = 880, 640
LARGURA_TABULEIRO, ALTURA_TABULEIRO = 640, 640
DIMENSAO = 8
TAMANHO_QUADRADO = LARGURA_TABULEIRO // DIMENSAO
LARGURA_PAINEL = LARGURA_TELA - LARGURA_TABULEIRO
FPS = 30

# Cores
COR_CLARA = pygame.Color(238, 238, 210)
COR_ESCURA = pygame.Color(118, 150, 86)
COR_DESTAQUE_SELECAO = pygame.Color(255, 255, 51, 160)
COR_DESTAQUE_ULTIMO_MOV = pygame.Color(170, 162, 58, 150)
COR_DESTAQUE_VALIDO = pygame.Color(0, 0, 0, 80)
COR_PAINEL = pygame.Color('gray20')
COR_TEXTO = pygame.Color('white')
COR_BOTAO = pygame.Color('gray30')
COR_BOTAO_DESISTIR = pygame.Color(180, 60, 60)
COR_RELOGIO_ATIVO = pygame.Color(120, 190, 120)

PECAS_UNICODE = {
    'P': '♙', 'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔',
    'p': '♟', 'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚'
}

# --- UTIL ---

def formatar_tempo(segundos: Optional[float]) -> str:
    if segundos is None: return "--:--"
    if segundos <= 0: return "00:00"
    minutos = math.floor(segundos / 60)
    segundos_restantes = math.floor(segundos % 60)
    return f"{minutos:02d}:{segundos_restantes:02d}"

# --- CLASSES ---
class BotHandler:
    def __init__(self, path: str):
        self.path = path
        self.stockfish: Optional[Stockfish] = None
        self.available = False
        self.init_stockfish()

    def init_stockfish(self):
        if not os.path.exists(self.path):
            self.available = False
            self.stockfish = None
            return
        try:
            # Parâmetros padrão - podem ser ajustados pelo jogador ao escolher dificuldade
            self.stockfish = Stockfish(path=self.path)
            self.stockfish.update_engine_parameters({
                "UCI_LimitStrength": True,
                "Skill Level": 5,
                "UCI_Elo": 1200
            })
            self.available = True
        except Exception as e:
            print("Falha ao inicializar Stockfish:", e)
            self.stockfish = None
            self.available = False

    def set_skill(self, skill_level: int):
        if not self.available: return
        # skill_level entre 0 e 20 normalmente; iremos mapear 0,3,7 para níveis distintos
        elo = 800 + skill_level * 150
        try:
            self.stockfish.update_engine_parameters({
                "Skill Level": skill_level,
                "UCI_LimitStrength": True,
                "UCI_Elo": max(200, min(3500, elo))
            })
        except Exception as e:
            print("Erro ao setar skill do Stockfish:", e)

    def best_move(self, fen: str, time_ms: int = 200) -> Optional[str]:
        """Retorna a melhor jogada em UCI. time_ms limita o tempo de pensamento. Retorna None se falhar."""
        if not self.available or not self.stockfish:
            return None
        try:
            self.stockfish.set_fen_position(fen)
            # usar get_best_move_time para limitar o tempo
            mv = self.stockfish.get_best_move_time(time_ms)
            return mv
        except Exception as e:
            print("Stockfish error:", e)
            return None


class GameState:
    def __init__(self):
        self.reset_game()

    def reset_game(self):
        self.board = chess.Board()
        self.move_stack = self.board.move_stack
        self.quadrado_selecionado: Optional[int] = None
        self.cliques_jogador: List[int] = []
        self.historico_san: List[str] = []
        self.update_historico()  # inicial
        self.resultado_final = ""

    def push_move(self, move: chess.Move):
        self.board.push(move)
        self.update_historico_incremental(move)

    def update_historico(self):
        self.historico_san = []
        temp_board = chess.Board()
        for i, mv in enumerate(self.board.move_stack):
            if i % 2 == 0:
                self.historico_san.append(f"{i//2 + 1}. {temp_board.san(mv)}")
            else:
                self.historico_san[-1] += f" {temp_board.san(mv)}"
            temp_board.push(mv)

    def update_historico_incremental(self, last_move: chess.Move):
        # atualiza apenas com a última jogada
        idx = len(self.board.move_stack) - 1
        temp_board = chess.Board()
        for i in range(idx):
            temp_board.push(self.board.move_stack[i])
        if idx % 2 == 0:
            self.historico_san.append(f"{idx//2 + 1}. {temp_board.san(last_move)}")
        else:
            self.historico_san[-1] += f" {temp_board.san(last_move)}"


class UIRenderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        # fontes (criar apenas uma vez)
        pygame.font.init()
        self.font_pecas = pygame.font.SysFont("Segoe UI Symbol", int(TAMANHO_QUADRADO * 0.8))
        self.font_painel_titulo = pygame.font.SysFont("helvetica", 32)
        self.font_painel_texto = pygame.font.SysFont("helvetica", 24)
        self.font_coordenadas = pygame.font.SysFont("helvetica", 16)
        self.font_menu = pygame.font.SysFont("helvetica", 50)
        self.font_relogio = pygame.font.SysFont("monospace", 40, bold=True)
        self.font_label = pygame.font.SysFont("helvetica", 20, bold=True)

        # imagens de avatar carregadas e escaladas
        self.imagens_bot = {}
        self.imagem_jogador = None
        self.avatar_tamanho = (80, 80)
        self.load_images()

        # precache surfaces
        self.surface_highlight = pygame.Surface((TAMANHO_QUADRADO, TAMANHO_QUADRADO), pygame.SRCALPHA)
        self.surface_highlight.fill(COR_DESTAQUE_SELECAO)
        self.surface_last_move = pygame.Surface((TAMANHO_QUADRADO, TAMANHO_QUADRADO), pygame.SRCALPHA)
        self.surface_last_move.fill(COR_DESTAQUE_ULTIMO_MOV)

    def load_images(self):
        expected = ["bagre.jpeg", "joi.jpeg", "mr_chess.jpg", "jogador.jpeg"]
        for name in expected:
            path = os.path.join(CAMINHO_IMAGENS, name)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    img = pygame.transform.scale(img, self.avatar_tamanho)
                    if name == "jogador.jpeg":
                        self.imagem_jogador = img
                    else:
                        key = "Bagre" if "bagre" in name else ("Joi" if "joi" in name else "Mr Chess")
                        self.imagens_bot[key] = img
                except Exception as e:
                    print("Erro ao carregar imagem", path, e)
            else:
                print("Imagem faltando:", path)

    def desenhar_texto(self, texto: str, fonte: pygame.font.Font, cor: pygame.Color, centro: Tuple[int, int]):
        obj = fonte.render(texto, True, cor)
        rect = obj.get_rect(center=centro)
        self.screen.blit(obj, rect)

    def desenhar_tabuleiro(self, tabuleiro_invertido: bool):
        for r in range(DIMENSAO):
            for c in range(DIMENSAO):
                cor = COR_CLARA if (r + c) % 2 == 0 else COR_ESCURA
                pygame.draw.rect(self.screen, cor, pygame.Rect(c * TAMANHO_QUADRADO, r * TAMANHO_QUADRADO, TAMANHO_QUADRADO, TAMANHO_QUADRADO))
                # coordenadas
                if tabuleiro_invertido:
                    quadrado_real = chess.square(7 - c, r)
                else:
                    quadrado_real = chess.square(c, 7 - r)
                coord = chess.SQUARE_NAMES[quadrado_real]
                texto = self.font_coordenadas.render(coord, True, COR_ESCURA if (r + c) % 2 == 0 else COR_CLARA)
                self.screen.blit(texto, (c * TAMANHO_QUADRADO + 2, r * TAMANHO_QUADRADO + 2))

    def desenhar_pecas(self, board: chess.Board, tabuleiro_invertido: bool):
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
            render_peca = self.font_pecas.render(simbolo, True, cor_peca)
            pos_x = c * TAMANHO_QUADRADO + (TAMANHO_QUADRADO - render_peca.get_width()) // 2
            pos_y = r * TAMANHO_QUADRADO + (TAMANHO_QUADRADO - render_peca.get_height()) // 2
            # sombra
            for off in [(1,1),(1,-1),(-1,1),(-1,-1)]:
                self.screen.blit(sombra, (pos_x + off[0], pos_y + off[1]))
            self.screen.blit(render_peca, (pos_x, pos_y))

    def get_pos_tela(self, quadrado: int, tabuleiro_invertido: bool) -> Tuple[int,int]:
        rank, file = chess.square_rank(quadrado), chess.square_file(quadrado)
        if tabuleiro_invertido:
            return rank, 7 - file
        else:
            return 7 - rank, file

    def desenhar_destaques(self, board: chess.Board, quadrado_selecionado: Optional[int], ultimo_mov: Optional[chess.Move], tabuleiro_invertido: bool):
        # último movimento
        if ultimo_mov:
            for q in [ultimo_mov.from_square, ultimo_mov.to_square]:
                r, c = self.get_pos_tela(q, tabuleiro_invertido)
                self.screen.blit(self.surface_last_move, (c * TAMANHO_QUADRADO, r * TAMANHO_QUADRADO))
        # seleção atual e movimentos válidos
        if quadrado_selecionado is not None:
            r_sel, c_sel = self.get_pos_tela(quadrado_selecionado, tabuleiro_invertido)
            self.screen.blit(self.surface_highlight, (c_sel * TAMANHO_QUADRADO, r_sel * TAMANHO_QUADRADO))
            # círculos para movimentos válidos
            s = pygame.Surface((TAMANHO_QUADRADO, TAMANHO_QUADRADO), pygame.SRCALPHA)
            s.fill(COR_DESTAQUE_VALIDO)
            for mv in board.legal_moves:
                if mv.from_square == quadrado_selecionado:
                    r_dest, c_dest = self.get_pos_tela(mv.to_square, tabuleiro_invertido)
                    centro = (c_dest * TAMANHO_QUADRADO + TAMANHO_QUADRADO // 2, r_dest * TAMANHO_QUADRADO + TAMANHO_QUADRADO // 2)
                    pygame.draw.circle(self.screen, s.get_at((0,0)), centro, 12)

    def desenhar_painel_info(self, board: chess.Board, tempo_brancas: Optional[float], tempo_pretas: Optional[float], historico_san: List[str], modo_jogo: Optional[str], skill_bot: Optional[int], cor_jogador: Optional[bool]) -> pygame.Rect:
        pygame.draw.rect(self.screen, COR_PAINEL, pygame.Rect(LARGURA_TABULEIRO, 0, LARGURA_PAINEL, ALTURA_TELA))
        centro_x = LARGURA_TABULEIRO + LARGURA_PAINEL // 2
        y = 20
        self.desenhar_texto("Adversário", self.font_label, COR_TEXTO, (centro_x, y))
        y += 30
        avatar = None
        if modo_jogo == "pvp":
            avatar = self.imagem_jogador
        elif modo_jogo == "pvb":
            if skill_bot == 0: avatar = self.imagens_bot.get("Bagre")
            elif skill_bot == 3: avatar = self.imagens_bot.get("Joi")
            elif skill_bot == 7: avatar = self.imagens_bot.get("Mr Chess")
        if avatar:
            avatar_rect = avatar.get_rect(center=(centro_x, y + self.avatar_tamanho[1] // 2))
            self.screen.blit(avatar, avatar_rect)
            y = avatar_rect.bottom + 10
        # relógio adversário
        cor_rel = COR_RELOGIO_ATIVO if board.turn != cor_jogador else COR_BOTAO
        rect_rel = pygame.Rect(LARGURA_TABULEIRO + 10, y, LARGURA_PAINEL - 20, 45)
        pygame.draw.rect(self.screen, cor_rel, rect_rel, border_radius=10)
        tempo_op = tempo_pretas if cor_jogador == chess.WHITE else tempo_brancas
        self.desenhar_texto(formatar_tempo(tempo_op), self.font_relogio, COR_TEXTO, rect_rel.center)
        y = rect_rel.bottom + 20
        # histórico (meio)
        self.desenhar_texto("Histórico", self.font_painel_texto, COR_TEXTO, (centro_x, y))
        y += 25
        for i, txt in enumerate(historico_san[-12:]):
            # somente desenha se houver espaço até a área inferior
            if y + i * 22 < ALTURA_TELA - 140:
                self.desenhar_texto(txt, self.font_painel_texto, COR_TEXTO, (centro_x, y + i * 22))
        # seção inferior: jogador e botão desistir
        y_inf = ALTURA_TELA - 20
        desistir_rect = pygame.Rect(LARGURA_TABULEIRO + 20, y_inf - 40, LARGURA_PAINEL - 40, 40)
        pygame.draw.rect(self.screen, COR_BOTAO_DESISTIR, desistir_rect, border_radius=10)
        self.desenhar_texto("Desistir", self.font_painel_texto, COR_TEXTO, desistir_rect.center)
        y_inf = desistir_rect.top - 10
        cor_rel_j = COR_RELOGIO_ATIVO if board.turn == cor_jogador else COR_BOTAO
        rect_rel_j = pygame.Rect(LARGURA_TABULEIRO + 10, y_inf - 45, LARGURA_PAINEL - 20, 45)
        pygame.draw.rect(self.screen, cor_rel_j, rect_rel_j, border_radius=10)
        tempo_j = tempo_brancas if cor_jogador == chess.WHITE or modo_jogo == "pvp" else tempo_pretas
        self.desenhar_texto(formatar_tempo(tempo_j), self.font_relogio, COR_TEXTO, rect_rel_j.center)
        # avatar jogador
        avatar_j_rect = self.imagem_jogador.get_rect(center=(centro_x, rect_rel_j.top - self.avatar_tamanho[1] // 2 - 5))
        self.screen.blit(self.imagem_jogador, avatar_j_rect)
        self.desenhar_texto("Jogador", self.font_label, COR_TEXTO, (centro_x, avatar_j_rect.top - 15))
        return desistir_rect

    def desenhar_tela_menu(self):
        self.screen.fill(COR_PAINEL)
        self.desenhar_texto("Xadrez", self.font_menu, COR_TEXTO, (LARGURA_TELA // 2, ALTURA_TELA // 4))
        pvp_rect = pygame.Rect(LARGURA_TELA // 2 - 200, ALTURA_TELA // 2 - 60, 400, 80)
        pvb_rect = pygame.Rect(LARGURA_TELA // 2 - 200, ALTURA_TELA // 2 + 40, 400, 80)
        pygame.draw.rect(self.screen, COR_BOTAO, pvp_rect, border_radius=10)
        pygame.draw.rect(self.screen, COR_BOTAO, pvb_rect, border_radius=10)
        self.desenhar_texto("Jogador vs Jogador", self.font_painel_titulo, COR_TEXTO, pvp_rect.center)
        self.desenhar_texto("Jogador vs Bot", self.font_painel_titulo, COR_TEXTO, pvb_rect.center)
        return pvp_rect, pvb_rect

    def desenhar_menu_dificuldade(self):
        self.screen.fill(COR_PAINEL)
        self.desenhar_texto("Escolha a Dificuldade", self.font_menu, COR_TEXTO, (LARGURA_TELA // 2, ALTURA_TELA // 4))
        facil_rect = pygame.Rect(LARGURA_TELA // 2 - 150, ALTURA_TELA // 2 - 100, 300, 60)
        medio_rect = pygame.Rect(LARGURA_TELA // 2 - 150, ALTURA_TELA // 2, 300, 60)
        dificil_rect = pygame.Rect(LARGURA_TELA // 2 - 150, ALTURA_TELA // 2 + 100, 300, 60)
        pygame.draw.rect(self.screen, COR_BOTAO, facil_rect, border_radius=10)
        pygame.draw.rect(self.screen, COR_BOTAO, medio_rect, border_radius=10)
        pygame.draw.rect(self.screen, COR_BOTAO, dificil_rect, border_radius=10)
        self.desenhar_texto("Bagre (Fácil)", self.font_painel_texto, COR_TEXTO, facil_rect.center)
        self.desenhar_texto("Joi (Médio)", self.font_painel_texto, COR_TEXTO, medio_rect.center)
        self.desenhar_texto("Mr Chess (Difícil)", self.font_painel_texto, COR_TEXTO, dificil_rect.center)
        return facil_rect, medio_rect, dificil_rect

    def desenhar_menu_cor(self):
        self.screen.fill(COR_PAINEL)
        self.desenhar_texto("Escolha sua cor", self.font_menu, COR_TEXTO, (LARGURA_TELA // 2, ALTURA_TELA // 4))
        brancas_rect = pygame.Rect(LARGURA_TELA // 2 - 200, ALTURA_TELA // 2, 180, 80)
        pretas_rect = pygame.Rect(LARGURA_TELA // 2 + 20, ALTURA_TELA // 2, 180, 80)
        pygame.draw.rect(self.screen, COR_BOTAO, brancas_rect, border_radius=10)
        pygame.draw.rect(self.screen, COR_BOTAO, pretas_rect, border_radius=10)
        self.desenhar_texto("Brancas", self.font_painel_titulo, COR_TEXTO, brancas_rect.center)
        self.desenhar_texto("Pretas", self.font_painel_titulo, COR_TEXTO, pretas_rect.center)
        return brancas_rect, pretas_rect

    def desenhar_menu_tempo(self):
        self.screen.fill(COR_PAINEL)
        self.desenhar_texto("Controle de Tempo", self.font_menu, COR_TEXTO, (LARGURA_TELA // 2, 100))
        opcoes = {"1 min": 60, "5 min": 300, "10 min": 600, "Sem Tempo": None}
        botoes = {}
        y = 200
        for txt, t in opcoes.items():
            rect = pygame.Rect(LARGURA_TELA // 2 - 150, y, 300, 60)
            pygame.draw.rect(self.screen, COR_BOTAO, rect, border_radius=10)
            self.desenhar_texto(txt, self.font_painel_titulo, COR_TEXTO, rect.center)
            botoes[txt] = (rect, t)
            y += 80
        return botoes

    def desenhar_tela_fim(self, resultado: str) -> pygame.Rect:
        overlay = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        overlay.fill((0,0,0,180))
        self.screen.blit(overlay, (0,0))
        self.desenhar_texto(resultado, self.font_menu, pygame.Color('gold'), (LARGURA_TELA // 2, ALTURA_TELA // 3))
        bot_rect = pygame.Rect(LARGURA_TELA // 2 - 150, ALTURA_TELA // 2, 300, 80)
        pygame.draw.rect(self.screen, COR_BOTAO, bot_rect, border_radius=10)
        self.desenhar_texto("Jogar Novamente", self.font_painel_titulo, COR_TEXTO, bot_rect.center)
        return bot_rect

    def promocao_modal(self, cor_brancas: bool) -> Optional[int]:
        """Mostra um modal simples para escolher promoção. Retorna constante chess.QUEEN/ROOK/BISHOP/KNIGHT."""
        choices = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        texts = ['Dama', 'Torre', 'Bispo', 'Cavalo']
        overlay = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        overlay.fill((0,0,0,180))
        self.screen.blit(overlay, (0,0))
        rects = []
        largura = 120
        total_w = largura * len(choices) + 20 * (len(choices)-1)
        x0 = LARGURA_TELA//2 - total_w//2
        y0 = ALTURA_TELA//2 - 40
        for i, t in enumerate(texts):
            r = pygame.Rect(x0 + i*(largura+20), y0, largura, 80)
            pygame.draw.rect(self.screen, COR_BOTAO, r, border_radius=8)
            self.desenhar_texto(t, self.font_painel_texto, COR_TEXTO, r.center)
            rects.append((r, choices[i]))
        pygame.display.flip()
        # loop modal
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if e.type == pygame.MOUSEBUTTONDOWN:
                    for r, val in rects:
                        if r.collidepoint(e.pos):
                            return val
            pygame.time.Clock().tick(30)


class MainLoop:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA))
        pygame.display.set_caption("Xadrez Completo v6")
        self.clock = pygame.time.Clock()
        self.ui = UIRenderer(self.screen)
        self.bot = BotHandler(NOME_EXECUTAVEL_STOCKFISH)
        self.state = GameState()
        # estado do menu
        self.estado_jogo = "MENU_PRINCIPAL"
        self.modo_jogo = None
        self.cor_jogador = None
        self.tabuleiro_invertido = False
        self.skill_bot = None
        # tempo
        self.tempo_inicial = None
        self.tempo_brancas = None
        self.tempo_pretas = None
        self.ultimo_update = pygame.time.get_ticks()
        # controladores
        self.pensando_bot = False
        self.tempo_pensamento_ms = 300  # tempo padrão para stockfish pensar (ajustável)
        # botão desistir cache
        self.desistir_rect_cache = None

    def verificar_recursos(self):
        msgs = []
        if not os.path.exists(NOME_EXECUTAVEL_STOCKFISH):
            msgs.append(f"Executável do Stockfish não encontrado em '{NOME_EXECUTAVEL_STOCKFISH}'")
        for name in ["bagre.jpeg","joi.jpeg","mr_chess.jpg","jogador.jpeg"]:
            if not os.path.exists(os.path.join(CAMINHO_IMAGENS, name)):
                msgs.append(f"Imagem '{name}' não encontrada em '{CAMINHO_IMAGENS}'")
        return msgs

    def run(self):
        msgs = self.verificar_recursos()
        if msgs:
            # mostra mensagens na tela e permite fechar
            self.screen.fill(COR_PAINEL)
            for i, m in enumerate(msgs):
                self.ui.desenhar_texto(m, self.ui.font_painel_texto, COR_TEXTO, (LARGURA_TELA//2, 100 + i*30))
            self.ui.desenhar_texto("Corrija os arquivos e reinicie.", self.ui.font_painel_texto, COR_TEXTO, (LARGURA_TELA//2, 200))
            pygame.display.flip()
            while True:
                for e in pygame.event.get():
                    if e.type == pygame.QUIT:
                        pygame.quit(); sys.exit()
                self.clock.tick(10)
        # loop principal
        while True:
            now = pygame.time.get_ticks()
            dt = now - self.ultimo_update
            self.ultimo_update = now
            self.handle_events()
            self.update(dt)
            self.render()
            self.clock.tick(FPS)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            # eventos por estado
            if self.estado_jogo == "MENU_PRINCIPAL":
                self.handle_menu_principal(event)
            elif self.estado_jogo == "MENU_DIFICULDADE":
                self.handle_menu_dificuldade(event)
            elif self.estado_jogo == "MENU_COR":
                self.handle_menu_cor(event)
            elif self.estado_jogo == "MENU_TEMPO":
                self.handle_menu_tempo(event)
            elif self.estado_jogo == "JOGANDO":
                self.handle_jogando(event)
            elif self.estado_jogo == "FIM_DE_JOGO":
                self.handle_fim(event)

    # --- Handlers de Menu ---
    def handle_menu_principal(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN: return
        pvp, pvb = self.ui.desenhar_tela_menu()
        if pvp.collidepoint(event.pos):
            self.modo_jogo = 'pvp'
            self.estado_jogo = 'MENU_TEMPO'
        elif pvb.collidepoint(event.pos):
            self.estado_jogo = 'MENU_DIFICULDADE'

    def handle_menu_dificuldade(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN: return
        fa, me, di = self.ui.desenhar_menu_dificuldade()
        if fa.collidepoint(event.pos):
            self.skill_bot = 0
        elif me.collidepoint(event.pos):
            self.skill_bot = 3
        elif di.collidepoint(event.pos):
            self.skill_bot = 7
        else:
            return
        # inicializa stockfish com skill
        if self.bot.available:
            self.bot.set_skill(self.skill_bot)
        self.modo_jogo = 'pvb'
        self.estado_jogo = 'MENU_COR'

    def handle_menu_cor(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN: return
        br, pr = self.ui.desenhar_menu_cor()
        if br.collidepoint(event.pos):
            self.cor_jogador = chess.WHITE
            self.tabuleiro_invertido = False
            self.estado_jogo = 'MENU_TEMPO'
        elif pr.collidepoint(event.pos):
            self.cor_jogador = chess.BLACK
            self.tabuleiro_invertido = True
            self.estado_jogo = 'MENU_TEMPO'

    def handle_menu_tempo(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN: return
        botoes = self.ui.desenhar_menu_tempo()
        for txt, (rect, tempo) in botoes.items():
            if rect.collidepoint(event.pos):
                self.tempo_inicial = tempo
                self.tempo_brancas = tempo
                self.tempo_pretas = tempo
                self.state.reset_game()
                self.estado_jogo = 'JOGANDO'
                self.ultimo_update = pygame.time.get_ticks()
                break

    # --- Jogando ---
    def handle_jogando(self, event):
        # re-cria desistir rect para area correta
        desistir_rect = pygame.Rect(LARGURA_TABULEIRO + 20, ALTURA_TELA - 60, LARGURA_PAINEL - 40, 40)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if desistir_rect.collidepoint(event.pos):
                vencedor = 'Pretas' if self.state.board.turn == chess.WHITE else 'Brancas'
                self.state.resultado_final = f"{vencedor} venceram por desistência."
                self.estado_jogo = 'FIM_DE_JOGO'
                return
            if event.pos[0] > LARGURA_TABULEIRO: return
            tela_c, tela_r = event.pos[0] // TAMANHO_QUADRADO, event.pos[1] // TAMANHO_QUADRADO
            if self.tabuleiro_invertido:
                quadrado_clicado = chess.square(7 - tela_c, tela_r)
            else:
                quadrado_clicado = chess.square(tela_c, 7 - tela_r)
            # Se não havia seleção ainda
            if not self.state.cliques_jogador:
                p = self.state.board.piece_at(quadrado_clicado)
                if p and p.color == self.state.board.turn:
                    # seleciona essa peça (permite re-seleção)
                    self.state.quadrado_selecionado = quadrado_clicado
                    self.state.cliques_jogador = [quadrado_clicado]
            else:
                # se clicar em outra peça da mesma cor, troca seleção
                p = self.state.board.piece_at(quadrado_clicado)
                if p and p.color == self.state.board.turn:
                    self.state.quadrado_selecionado = quadrado_clicado
                    self.state.cliques_jogador = [quadrado_clicado]
                    return
                movimento = chess.Move(self.state.cliques_jogador[0], quadrado_clicado)
                # promoção automática -> modal para escolher
                if self.state.board.piece_type_at(self.state.cliques_jogador[0]) == chess.PAWN and chess.square_rank(quadrado_clicado) in [0,7]:
                    # abrir modal
                    promo = self.ui.promocao_modal(self.cor_jogador == chess.WHITE)
                    if promo:
                        movimento.promotion = promo
                if movimento in self.state.board.legal_moves:
                    self.state.push_move(movimento)
                    self.state.quadrado_selecionado = None
                    self.state.cliques_jogador = []

    def update(self, dt_ms: int):
        # atualização do relógio se houver controle de tempo
        if self.estado_jogo == 'JOGANDO' and self.tempo_inicial is not None:
            # se bot estiver pensando, não decrementa o tempo do jogador (pausa)
            if not (self.modo_jogo == 'pvb' and self.pensando_bot):
                if self.state.board.turn == chess.WHITE:
                    if self.tempo_brancas is not None:
                        self.tempo_brancas -= dt_ms / 1000.0
                else:
                    if self.tempo_pretas is not None:
                        self.tempo_pretas -= dt_ms / 1000.0
                # checar timeout
                if self.tempo_brancas is not None and self.tempo_brancas <= 0:
                    self.state.resultado_final = 'Pretas venceram no tempo!'
                    self.estado_jogo = 'FIM_DE_JOGO'
                elif self.tempo_pretas is not None and self.tempo_pretas <= 0:
                    self.state.resultado_final = 'Brancas venceram no tempo!'
                    self.estado_jogo = 'FIM_DE_JOGO'
        # vez do bot
        if self.estado_jogo == 'JOGANDO' and self.modo_jogo == 'pvb' and self.state.board.turn != self.cor_jogador and not self.state.board.is_game_over():
            # chamar bot
            if self.bot.available:
                # indica que o bot está pensando para pausar o relógio
                if not self.pensando_bot:
                    self.pensando_bot = True
                # obter melhor jogada (limitando tempo)
                mv_uci = self.bot.best_move(self.state.board.fen(), time_ms=self.tempo_pensamento_ms)
                if mv_uci:
                    try:
                        self.state.push_move(chess.Move.from_uci(mv_uci))
                    except Exception as e:
                        print("Erro aplicando move do bot:", e)
                else:
                    # fallback: tentar get_best_move sem tempo ou random legal
                    try:
                        mv = self.bot.stockfish.get_best_move() if self.bot.stockfish else None
                        if mv:
                            self.state.push_move(chess.Move.from_uci(mv))
                        else:
                            # jogada aleatória segura
                            import random
                            moves = list(self.state.board.legal_moves)
                            if moves:
                                self.state.push_move(random.choice(moves))
                    except Exception as e:
                        print("Fallback bot falhou:", e)
                self.pensando_bot = False
            else:
                # bot indisponível -> empata por desistência do bot
                self.state.resultado_final = 'Bot indisponível. Empate.'
                self.estado_jogo = 'FIM_DE_JOGO'

        # checar fim de jogo por condições de tabuleiro
        if self.estado_jogo == 'JOGANDO' and self.state.board.is_game_over():
            if self.state.board.is_checkmate():
                vencedor = 'Pretas' if self.state.board.turn == chess.WHITE else 'Brancas'
                self.state.resultado_final = f"Xeque-mate! {vencedor} venceram."
            else:
                self.state.resultado_final = 'Empate!'
            self.estado_jogo = 'FIM_DE_JOGO'

    def render(self):
        if self.estado_jogo == 'MENU_PRINCIPAL':
            self.ui.desenhar_tela_menu()
            pygame.display.flip(); return
        if self.estado_jogo == 'MENU_DIFICULDADE':
            self.ui.desenhar_menu_dificuldade(); pygame.display.flip(); return
        if self.estado_jogo == 'MENU_COR':
            self.ui.desenhar_menu_cor(); pygame.display.flip(); return
        if self.estado_jogo == 'MENU_TEMPO':
            self.ui.desenhar_menu_tempo(); pygame.display.flip(); return

        # telas de jogo e fim
        self.ui.desenhar_tabuleiro(self.tabuleiro_invertido)
        ultimo_mov = self.state.board.peek() if self.state.board.move_stack else None
        self.ui.desenhar_destaques(self.state.board, self.state.quadrado_selecionado, ultimo_mov, self.tabuleiro_invertido)
        self.ui.desenhar_pecas(self.state.board, self.tabuleiro_invertido)
        # painel
        self.desistir_rect_cache = self.ui.desenhar_painel_info(self.state.board, self.tempo_brancas, self.tempo_pretas, self.state.historico_san, self.modo_jogo, self.skill_bot, self.cor_jogador)
        pygame.display.flip()

        if self.estado_jogo == 'FIM_DE_JOGO':
            bot_reset = self.ui.desenhar_tela_fim(self.state.resultado_final)
            pygame.display.flip()
            # aguarda clique para reset
            for e in pygame.event.get():
                if e.type == pygame.MOUSEBUTTONDOWN and bot_reset.collidepoint(e.pos):
                    self.reset_to_menu()

    def handle_fim(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN: return
        # se clicar no botão da tela de fim (render faz esse passo adicional)
        # apenas volta pra menu
        self.reset_to_menu()

    def reset_to_menu(self):
        self.estado_jogo = 'MENU_PRINCIPAL'
        self.modo_jogo = None
        self.cor_jogador = None
        self.tabuleiro_invertido = False
        self.skill_bot = None
        self.tempo_inicial = None
        self.tempo_brancas = None
        self.tempo_pretas = None
        self.pensando_bot = False
        self.state.reset_game()


if __name__ == '__main__':
    MainLoop().run()
