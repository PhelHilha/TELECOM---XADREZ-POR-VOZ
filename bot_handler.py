import os
import queue
from multiprocessing import Process, Queue
from stockfish import Stockfish

class BotHandler:
    def __init__(self, path="stockfish.exe", default_think_ms=2000):

        # path: caminho pro stockfish
        # default_think_ms: tempo q o bot deve pensar usando get_best_move_time
        
        self.path = path
        self.available = False
        self.think_time_ms = max(50, int(default_think_ms))
        self._process = None
        self._result_queue = None
        self._init_engine_check()


    # inicialização e as configurações

    def _init_engine_check(self):
        if not os.path.exists(self.path):
            print(f"Aviso: Stockfish não encontrado em '{self.path}'. Bot ficará indisponível.")
            self.available = False
        else:
            self.available = True

    def set_think_time(self, ms: int):
        self.think_time_ms = max(50, int(ms))

    def configure_skill(self, skill: int):
        
        # só armazena o nível de dificuldade para ser usado quando o processo for criado.

        self.skill_level = max(0, min(20, int(skill)))


    # Execução isolada em processo

    @staticmethod
    def _think_worker_process(fen, think_ms, result_q, path, skill):
        # função que roda em processo separado
        try:
            stockfish = Stockfish(path=path)
            stockfish.update_engine_parameters({
                "UCI_LimitStrength": True,
                "Skill Level": skill,
                "UCI_Elo": 800 + skill * 200
            })
            stockfish.set_fen_position(fen)
            mv = None
            try:
                mv = stockfish.get_best_move_time(think_ms)
            except Exception:
                mv = stockfish.get_best_move()
            result_q.put(mv)
        except Exception as e:
            print("Erro no processo do bot:", e)
            result_q.put(None)

    def start_thinking(self, fen: str, result_q: queue.Queue = None, think_ms: int = None):
        
        # inicia o processo do bot e o resultado vai ser colocado em result_q.
        
        if not self.available:
            print("Bot não disponível.")
            return None

        if think_ms is None:
            think_ms = self.think_time_ms
        if result_q is None:
            result_q = Queue()

        # evita iniciar dois processos ao mesmo tempo
        if self._process and self._process.is_alive():
            return self._result_queue

        # inicia o processo separado
        p = Process(target=BotHandler._think_worker_process,
                    args=(fen, think_ms, result_q, self.path, getattr(self, "skill_level", 5)),
                    daemon=True)
        p.start()
        self._process = p
        self._result_queue = result_q
        return result_q

    def is_thinking(self) -> bool:
        return self._process is not None and self._process.is_alive()

    def get_result_queue(self):
        return self._result_queue
