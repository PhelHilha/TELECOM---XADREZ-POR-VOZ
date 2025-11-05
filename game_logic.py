# game_logic.py

import chess

def move_to_custom_notation(move: chess.Move):
    """
    Converte um movimento UCI ('a2a4') para notação numérica '1-2 → 1-4'.
    """
    file_map = {'a': '1', 'b': '2', 'c': '3', 'd': '4',
                'e': '5', 'f': '6', 'g': '7', 'h': '8'}
    uci = move.uci()  # Exemplo: 'a2a4'
    col_from = file_map[uci[0]]
    lin_from = uci[1]
    col_to = file_map[uci[2]]
    lin_to = uci[3]
    return f"{col_from}-{lin_from} → {col_to}-{lin_to}"


class GameState:
    def __init__(self):
        self.reset_game()

    def reset_game(self):
        self.board = chess.Board()
        self.quadrado_selecionado = None
        self.cliques_jogador = []
        self.historico_san = []
        self.resultado_final = ""
        self.pending_promotion = None  # {'from': sq_from, 'to': sq_to}
        self.update_historico_full()

    def push_move(self, move: chess.Move):
        """
        Aplica a jogada ao tabuleiro e atualiza histórico incrementalmente.
        """
        self.board.push(move)
        self.update_historico_incremental(move)

    def update_historico_full(self):
        self.historico_san = []
        for i, mv in enumerate(self.board.move_stack):
            move_txt = move_to_custom_notation(mv)
            if i % 2 == 0:
                self.historico_san.append(f"{i//2 + 1}. {move_txt}")
            else:
                self.historico_san[-1] += f"   {move_txt}"

    def update_historico_incremental(self, last_move: chess.Move):
        idx = len(self.board.move_stack) - 1
        move_txt = move_to_custom_notation(last_move)
        if idx % 2 == 0:
            self.historico_san.append(f"{idx//2 + 1}. {move_txt}")
        else:
            self.historico_san[-1] += f"   {move_txt}"
