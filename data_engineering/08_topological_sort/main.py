from typing import Any

# =========
# 独自例外クラス
# =========
class RecursionException(Exception):
    pass

# =========
# logging
# =========


# =========
# メイン：DBオブジェクトの依存関係を整理し返す
# =========
class CompileDbt():

    def __init__(self):

        # 結果リスト
        self.res = []
        # 現在のサイクル中のループを検知
        self.cycle = set()
        # あるサイクルですでに訪問済みのノードを記録
        self.visit = set()
    
    def compile(self, graph:dict[str, list]) -> list[str]:
        # 他のメソッドからも呼べるようにする
        self.res.clear()
        self.visit.clear()
        self.cycle.clear()
    
        # =======
        # nodeを受け取り、再起的に依存ノードを探索する
        # 同じサイクル内で探索済みのノードに当たった場合、ループ参照となるため、処理を中止
        # 別のサイクルですでに探索済みノードにぶつかった場合、そこで探索を終了。（重複して依存ノードに追加することを防止）
        # =======
        def build_recursive(node:str) -> None:

            print(f"node:{node}, visit:{self.visit}, cycle:{self.cycle},res:{self.res}")

            # 同じサイクルで探索済みの場合False
            if node in self.cycle:
                raise RecursionException(f"循環参照が発生。処理を中断します: node:{node}, visit:{self.visit}, cycle:{self.cycle},res:{self.res}")
            # 別サイクルで探索済みならTrue
            if node in self.visit:
                return
            
            self.cycle.add(node)
            
            # このノードに関連する依存関係を洗う
            # 依存先が外部テーブル（この依存関係に定義されていない）可能性があるため、get[]とする
            for n1 in graph.get(node, []):
                build_recursive(n1)
            
            # サイクルの終端まで到達。visitから除外
            self.cycle.remove(node)

            # 探索済みnodeに追加
            self.visit.add(node)

            # 結果リストに追加
            self.res.append(node)

            return

        for n in graph:
            build_recursive(n)
        
        return self.res
        

# =========
# エントリーポイント
# =========
def main():
    print("====処理開始====")

    dependency_graph = {
        "stg_users": [],                    # 親はなし（Rawデータから直接作る）
        "stg_orders": [],                   # 親はなし
        "dim_users": ["stg_users"],         # stg_users が先に作られてないとダメ
        "fct_orders": ["stg_orders", "dim_users"], # 2つのテーブルに依存している
        "analytics_dashboard": ["fct_orders"] # 最下流のモデル
    }

    compiler = CompileDbt()
    res = compiler.compile(dependency_graph)
    print(res)

if __name__ == '__main__':
    main()

        


