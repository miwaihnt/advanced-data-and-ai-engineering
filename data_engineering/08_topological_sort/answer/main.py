import logging
from typing import Mapping, Iterable, List, Set

# ====== 
# loggingの設定
# ====== 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CircularDependencyError(ValueError):
    """データパイプラインの循環参照を検知した際のカスタム例外（ValueErrorを継承）"""
    pass


class dbtDAGCompiler:
    def __init__(self):
        # 1. 探索中（Visiting）の状態を管理するセット：循環参照の検知用
        self.visiting: Set[str] = set()
        # 2. 探索完了（Visited）の状態を管理するセット：別ルートからの重複処理をパスする用
        self.visited_complete: Set[str] = set()
        # 実行（ビルド）順序を格納するリスト
        self.build_order: List[str] = []

    def compile(self, graph: Mapping[str, Iterable[str]]) -> List[str]:
        """
        外部から依存関係グラフを受け取り、トポロジカルソートを実行して正しい順序を返す。
        循環参照がある場合は即座に例外を投げてプロセスを殺す（Fail-Fast）。
        """
        # クラスの状態を初期化（使い回せるように）
        self.visiting.clear()
        self.visited_complete.clear()
        self.build_order.clear()

        # ヘルパー関数（内部でのDFS再帰）
        def dfs(node: str) -> None:
            # 早期検問A: 今まさに掘り進めているルート上のノードに再会 ➔ 循環参照確定！
            if node in self.visiting:
                raise CircularDependencyError(
                    f"致命的な依存関係エラー：循環参照が検出されました。不健全なノード: {node}"
                )

            # 早期検問B: すでに過去の別ルートで安全性が確認・確定しているノード ➔ スキップ
            if node in self.visited_complete:
                return

            # 現在のノードを「探索中」としてマーク（色を塗る）
            self.visiting.add(node)

            # nodeが依存している親たち（graph[node]）を再帰的に掘り下げる
            # 💡 graphに定義されていない未知の親テーブルが指定された場合を考慮して .get() を使うのがDEの防衛策
            for parent in graph.get(node, []):
                dfs(parent)  # ➔ 正常ならNoneが返り、中でエラーがあれば例外が上まで突き抜ける！

            # 親たちのビルド順がすべて無事に確定したら、自分の「探索中」マークを外す
            self.visiting.remove(node)
            # 自分の「探索完了」マークをつける
            self.visited_complete.add(node)
            
            # 自分が安全にビルドできる状態になったので、実行リストの末尾に追加する
            self.build_order.append(node)

        # グラフ内のすべてのモデルを起点にしてDFSを回す（孤立ノードも確実に救うため）
        for model in graph:
            if model not in self.visited_complete:
                dfs(model)

        return self.build_order


def main():
    # 🟢 テストケース1: 正常なDAG（依存関係あり、孤立あり）
    normal_graph = {
        "stg_users": [],
        "stg_orders": [],
        "dim_users": ["stg_users"],
        "fct_orders": ["stg_orders", "dim_users"],
        "analytics_dashboard": ["fct_orders"],
        "isolated_table": []  # 孤立しているマスタテーブルなど
    }

    # 🔴 テストケース2: アナリストがやらかした循環参照（無限ループ）
    # あんたが仕込んだイジワルなテストデータを拝借するわよ！
    circular_graph = {
        "stg_users": [],
        "stg_orders": [],
        "dim_users": ["stg_users"],
        "fct_orders": ["stg_orders", "dim_users"],
        "analytics_dashboard": ["fct_orders", "llm_traning"],
        "llm_traning": ["analytics_dashboard"]
    }

    compiler = dbtDAGCompiler()

    print("--- 🟢 正常系のコンパイルテスト ---")
    try:
        order = compiler.compile(normal_graph)
        print(f"ビルド順序の確定結果:\n{order}\n")
    except CircularDependencyError as e:
        logger.error(f"正常系でエラーが発生（バグ）: {e}")

    print("--- 🔴 異常系（循環参照）のコンパイルテスト ---")
    try:
        # Fail-Fast思想：エラーが出たらダラダラ続けず、ここでキャッチしてメイン処理を美しく終了させる
        bad_order = compiler.compile(circular_graph)
        print(f"ビルド順序: {bad_order}")
    except CircularDependencyError as e:
        print(f"🔥 狙い通りにシステムが安全に爆死（Fail-Fast完了）:\n{e}")


if __name__ == '__main__':
    main()