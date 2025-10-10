import os
import threading
import queue
from stockfish import Stockfish

class BotHandler:
    def __init__(self, path="stockfish.exe", default_think_ms=2000):
        """
        path: caminho para stockfish
        default_think_ms: tempo (ms) que o bot deve pensar usando get_best_move_time
        """
        self.path = path
        self.stockfish = None
        self.available = False
        self.think_time_ms = max(50, int(default_think_ms))
        self._worker_thread = None
        self._result_queue = None
        self._stop_event = threading.Event()
        self._init_engine()

    def _init_engine(self):
        if not os.path.exists(self.path):
            print(f"Aviso: Stockfish não encontrado em '{self.path}'. Bot ficará indisponível.")
            self.available = False
            return
        try:
            self.stockfish = Stockfish(path=self.path)
            # parâmetros padrão (ajuste via configure_skill)
            self.stockfish.update_engine_parameters({
                "UCI_LimitStrength": True,
                "Skill Level": 5,
                "UCI_Elo": 1200
            })
            self.available = True
        except Exception as e:
            print("Erro ao inicializar Stockfish:", e)
            self.available = False

    def set_think_time(self, ms: int):
        self.think_time_ms = max(50, int(ms))

    def configure_skill(self, skill: int):
        if not self.available or not self.stockfish:
            return
        elo = 800 + skill * 200
        try:
            self.stockfish.update_engine_parameters({
                "Skill Level": skill,
                "UCI_LimitStrength": True,
                "UCI_Elo": max(200, min(3500, elo))
            })
        except Exception as e:
            print("Erro ao configurar skill do Stockfish:", e)

    def _think_worker(self, fen: str, result_q: queue.Queue, think_ms: int):
        """Executa em thread separado; coloca a jogada (ou None) em result_q."""
        try:
            if not self.available or not self.stockfish:
                result_q.put(None)
                return
            # set position e buscar melhor jogada por tempo limitado
            self.stockfish.set_fen_position(fen)
            mv = None
            try:
                mv = self.stockfish.get_best_move_time(think_ms)
            except Exception:
                # fallback para get_best_move
                try:
                    mv = self.stockfish.get_best_move()
                except Exception:
                    mv = None
            result_q.put(mv)
        except Exception as e:
            print("Erro no worker do bot:", e)
            result_q.put(None)

    def start_thinking(self, fen: str, result_q: queue.Queue = None, think_ms: int = None):
        """
        Inicia o pensamento do bot em background. Resultado será colocado em result_q (queue.Queue).
        Se não fornecer result_q, cria internamente uma e retorna.
        Retorna a queue que receberá a string UCI (ou None) quando terminar.
        """
        if think_ms is None:
            think_ms = self.think_time_ms
        if result_q is None:
            result_q = queue.Queue()
        # se thread anterior ainda viva, não tentar iniciar outra
        if self._worker_thread and self._worker_thread.is_alive():
            # opcional: não iniciar duas vezes
            return result_q
        self._stop_event.clear()
        t = threading.Thread(target=self._think_worker, args=(fen, result_q, think_ms), daemon=True)
        self._worker_thread = t
        self._result_queue = result_q
        t.start()
        return result_q

    def is_thinking(self) -> bool:
        return self._worker_thread is not None and self._worker_thread.is_alive()

    def get_result_queue(self):
        return self._result_queue
