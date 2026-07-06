import logging
import lancedb
import pyarrow as pa
import time
import numpy as np
from pathlib import Path
from typing import Union

from rag_primitive.core.config import settings
from rag_primitive.core.utils import JapaneseTokenizer # 🚀 これを使うわよ！

logger = logging.getLogger(__name__)


class LanceDBClient:
    """
    LanceDB への接続とデータ操作を担当する。
    「Phase 3: Storage」の責任を負う。
    """

    def __init__(self, uri: str = None):
        self.uri = uri or settings.LANCEDB_URI
        # 接続 (ディレクトリがなければ自動生成される)
        self.db = lancedb.connect(self.uri)
        self.table_name = settings.TABLE_NAME

    def _get_schema(self, vector_dim: int) -> pa.Schema:
        """
        テーブルの Arrow スキーマを定義する。
        """
        # フィールド名を指定せず、デフォルト（通常は 'item'）に任せるのよ！
        vector_type = pa.list_(pa.float32(), vector_dim)

        return pa.schema([
            pa.field("chunk_id", pa.string(), nullable=False),
            pa.field("speech_id", pa.string(), nullable=False),
            pa.field("content", pa.string(), nullable=False),
            pa.field("content_tokenized", pa.string(), nullable=False), # 🚀 全文検索用の分かち書きカラムよ！
            pa.field("speaker", pa.string(), nullable=False),
            pa.field("date", pa.string(), nullable=False),
            pa.field("meeting_name", pa.string(), nullable=False),
            # ベクトルカラム (固定次元数)
            pa.field("vector", vector_type, nullable=False),
        ])

    def get_or_create_table(self, vector_dim: int = 384):
        """
        テーブルを取得、存在しない場合は新規作成する。
        """
        if self.table_name in self.db.table_names():
            logger.info(f"Opening existing table: [bold cyan]{self.table_name}[/bold cyan]")
            return self.db.open_table(self.table_name)
        
        logger.info(f"Creating new table: [bold cyan]{self.table_name}[/bold cyan]")
        schema = self._get_schema(vector_dim)
        # スキーマを指定して空のテーブルを作成
        return self.db.create_table(self.table_name, schema=schema)

    def upsert_data(self, data: Union[pa.Table, pa.RecordBatchReader]):
        """
        データを Upsert (Update or Insert) する。
        chunk_id を一意識別子として使用する。
        """
        table = self.get_or_create_table()
        
        logger.info(f"Upserting data into [bold cyan]{self.table_name}[/bold cyan]...")
        
        (
            table.merge_insert("chunk_id")
            .when_matched_update_all()
            .when_not_matched_insert_all()
            .execute(data)
        )
        
        logger.info(f"Upsert complete. Total rows: [bold green]{len(table)}[/bold green]")

    def create_index(self, index_type: str = "HNSW"):
        """
        指定されたタイプのインデックスをベクトルカラムに構築する。
        """
        table = self.get_or_create_table()
        start_time = time.time()

        logger.info(f"Creating index: [bold cyan]{index_type}[/bold cyan] on [bold cyan]{self.table_name}[/bold cyan]...")

        try:
            idx_type = index_type.upper().replace("-", "_")

            if idx_type in ["HNSW", "IVF_HNSW_PQ"]:
                table.create_index(
                    metric="cosine",
                    index_type="IVF_HNSW_PQ",
                    num_partitions=256,
                    num_sub_vectors=96,
                    m=16,
                    ef_construction=100,
                    replace=True
                )
            elif idx_type == "IVF_PQ":
                table.create_index(
                    metric="cosine",
                    index_type="IVF_PQ",
                    num_partitions=256,
                    num_sub_vectors=96,
                    replace=True
                )
            else:
                logger.error(f"Unknown index type: [bold red]{index_type}[/bold red]")
                return

            elapsed_time = time.time() - start_time
            logger.info(f"Finished creating [bold green]{index_type}[/bold green] index. Time: [bold yellow]{elapsed_time:.2f}[/bold yellow] seconds")
        except Exception as e:
            logger.error(f"Failed to create index: {e}")

    def create_fts_index(self, column: str = "content_tokenized"):
        """
        指定されたカラムに全文検索（FTS）インデックスを構築するわ。
        """
        table = self.get_or_create_table()
        logger.info(f"Creating FTS index on column: [bold cyan]{column}[/bold cyan]...")
        
        # tokenizer_name="whitespace" を指定するのがコツよ！
        table.create_fts_index(column, tokenizer_name="whitespace", replace=True)
        
        logger.info(f"FTS index created successfully on [bold green]{self.table_name}[/bold green].")

    def drop_index(self, name: str = None):
        """
        既存のベクトルインデックスを削除する。
        """
        table = self.get_or_create_table()
        
        try:
            indices = table.list_indices()
            if not indices:
                logger.warning("No indices found to drop.")
                return

            if name:
                logger.info(f"Dropping index: [bold cyan]{name}[/bold cyan]...")
                table.drop_index(name)
            else:
                for idx in indices:
                    target_name = getattr(idx, "index_name", getattr(idx, "name", None))
                    if target_name:
                        logger.info(f"Dropping index: [bold cyan]{target_name}[/bold cyan]...")
                        table.drop_index(target_name)
            
            table.optimize()
            logger.info("Index(es) dropped and table optimized.")
        except Exception as e:
            logger.error(f"Failed to drop index: {e}")

    def search(self, query_vector: Union[list, np.ndarray], limit: int = 5):
        """
        ベクトル検索を実行し、類似度の高いチャンクを返す。
        """
        table = self.get_or_create_table()
        start = time.time()
        
        results = (
            table.search(query_vector)
            .limit(limit)
            .select(["content", "content_tokenized", "speaker", "date", "meeting_name", "chunk_id"])
            .to_list()
        )

        elapsed_time = time.time() - start
        logger.info(f"Vector search finished: time:{elapsed_time:.4f}s")
        
        return results

    def search_fts(self, query_text: str, limit: int = 5):
        """
        全文検索（FTS）を実行し、キーワード一致度の高いチャンクを返すわ。
        """
        table = self.get_or_create_table()
        start = time.time()

        # 🚀 検索クエリも分かち書きして、Tantivy に「これ単語の羅列よ」って教えてあげるの
        tokenizer = JapaneseTokenizer()
        tokenized_query = tokenizer.tokenize(query_text)
        logger.info(f"FTS Query (Tokenized): [bold yellow]{tokenized_query}[/bold yellow]")

        results = (
            table.search(tokenized_query, query_type="fts")
            .limit(limit)
            .select(["content", "content_tokenized", "speaker", "date", "meeting_name", "chunk_id"])
            .to_list()
        )

        elapsed_time = time.time() - start
        logger.info(f"FTS search finished: time:{elapsed_time:.4f}s")
        
        return results

    def search_hybrid_manual(self, query_text: str, query_vector: list, limit: int = 5, k: int = 60):
        """
        ベクトル検索と全文検索の結果を RRF で統合し、さらに上位候補を Cross-Encoder で再評価（リランク）するわ！
        API料金0円、ローカル環境最強の 2-Stage Retrieval よ！
        """
        from rag_primitive.embedding.model import SpeechReranker

        start = time.time()

        # 1. Retrieval Phase: 両方の手法で候補を多めに取得
        candidate_limit = max(limit * 10, 50)
        
        vec_results = self.search(query_vector, limit=candidate_limit)
        fts_results = self.search_fts(query_text, limit=candidate_limit)

        # 2. RRF (Reciprocal Rank Fusion) Score Calculation
        rrf_map = {}
        # ベクトル検索のランク付け
        for i, res in enumerate(vec_results):
            cid = res['chunk_id']
            rrf_map[cid] = {"rrf_score": 1.0 / (k + i + 1), "data": res}

        # 全文検索の結果を統合
        for i, res in enumerate(fts_results):
            cid = res['chunk_id']
            score = 1.0 / (k + i + 1)
            if cid in rrf_map:
                rrf_map[cid]["rrf_score"] += score
            else:
                rrf_map[cid] = {"rrf_score": score, "data": res}

        # RRF スコアでソートして、リランクにかける上位候補を絞り込む
        top_candidates = sorted(
            rrf_map.values(), 
            key=lambda x: x["rrf_score"], 
            reverse=True
        )[:candidate_limit]

        if not top_candidates:
            return []

        # 3. Reranking Phase: Cross-Encoder による精密な再評価
        logger.info(f"Reranking {len(top_candidates)} candidates with Cross-Encoder...")
        
        reranker = SpeechReranker()
        contents = [c["data"]["content"] for c in top_candidates]
        rerank_scores = reranker.compute_scores(query_text, contents)

        # 4. Final Integration: リランカースコアで最終順位を決定
        final_results = []
        for i, cand in enumerate(top_candidates):
            res = cand["data"]
            res["_rrf_score"] = cand["rrf_score"]
            res["_rerank_score"] = rerank_scores[i]
            final_results.append(res)

        # リランカースコア（高いほど良い）で降順ソート
        final_results.sort(key=lambda x: x["_rerank_score"], reverse=True)

        elapsed_time = time.time() - start
        logger.info(f"Hybrid (RRF + Cross-Encoder Rerank) finished: time:{elapsed_time:.4f}s")
        
        return final_results[:limit]
