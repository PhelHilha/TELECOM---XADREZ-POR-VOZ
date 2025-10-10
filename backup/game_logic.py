# game_logic.py
import chess

class GameState:
    def __init__(self):
        self.reset_game()

    def reset_game(self):
        self.board = chess.Board()
        self.quadrado_selecionado = None
        self.cliques_jogador = []
        self.historico_san = []
        self.resultado_final = ""
        # preencher histórico inicial (vazio)
        self.update_historico_full()

    def push_move(self, move: chess.Move):
        """
        Aplica a jogada ao tabuleiro e atualiza histórico incrementalmente.
        """
        self.board.push(move)
        self.update_historico_incremental(move)

    def update_historico_full(self):
        self.historico_san = []
        temp = chess.Board()
        for i, mv in enumerate(self.board.move_stack):
            if i % 2 == 0:
                self.historico_san.append(f"{i//2 + 1}. {temp.san(mv)}")
            else:
                self.historico_san[-1] += f" {temp.san(mv)}"
            temp.push(mv)

    def update_historico_incremental(self, last_move: chess.Move):
        idx = len(self.board.move_stack) - 1
        tmp = chess.Board()
        for i in range(idx):
            tmp.push(self.board.move_stack[i])
        if idx % 2 == 0:
            self.historico_san.append(f"{idx//2 + 1}. {tmp.san(last_move)}")
        else:
            self.historico_san[-1] += f" {tmp.san(last_move)}"
