import asyncio
import logging
import sys
import argparse
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich import box

from rag_primitive.core.logging import setup_logging
from rag_primitive.embedding.model import SpeechEmbedder
from rag_primitive.storage.lancedb_client import LanceDBClient

# コンソールの初期化
console = Console()
logger = logging.getLogger("rag_primitive.search")

def display_results(results: list, title: str, border_style: str = "cyan"):
    """検索結果を綺麗に表示するわ。"""
    if not results:
        console.print(f"[bold red]No results found for {title}.[/bold red]")
        return

    console.print(f"\n[bold {border_style}]--- {title} (Top {len(results)}) ---[/bold {border_style}]\n")
    
    for i, res in enumerate(results):
        # スコアの取得
        distance = res.get("_distance")
        fts_score = res.get("_score")
        rrf_score = res.get("_rrf_score")
        rerank_score = res.get("_rerank_score")
        
        meta_table = Table(show_header=False, box=box.SIMPLE_HEAD, padding=(0, 1))
        meta_table.add_row("[bold magenta]Speaker:[/bold magenta]", res['speaker'])
        meta_table.add_row("[bold magenta]Date:[/bold magenta]", res['date'])
        meta_table.add_row("[bold magenta]Meeting:[/bold magenta]", res['meeting_name'])
        
        if distance is not None:
            meta_table.add_row("[bold magenta]Vector Dist:[/bold magenta]", f"{distance:.4f}")
        if fts_score is not None:
            meta_table.add_row("[bold magenta]BM25 Score:[/bold magenta]", f"{fts_score:.4f}")
        if rrf_score is not None:
            meta_table.add_row("[bold magenta]RRF Score:[/bold magenta]", f"{rrf_score:.4f}")
        if rerank_score is not None:
            meta_table.add_row("[bold magenta]Rerank Score:[/bold magenta]", f"{rerank_score:.4f}")

        # チャンク内容の表示
        content_display = f"{res['content']}\n\n[dim]Tokens: {res['content_tokenized']}[/dim]"

        console.print(Panel(
            content_display,
            title=f"[{border_style}]Result #{i+1}[/{border_style}]",
            expand=False,
            border_style=border_style
        ))
        console.print(meta_table)
        console.print("-" * 40)

async def perform_hybrid_search(query_text: str, top_k: int = 3, mode: str = "both"):
    """
    ベクトル検索、全文検索、またはハイブリッド検索を実行するわ。
    """
    client = LanceDBClient()
    embedder = SpeechEmbedder()

    console.print(f"\n[bold yellow]Query:[/bold yellow] {query_text}")

    # 埋め込みベクトルの生成 (Hybrid と Vector で使うわ)
    query_vector = None
    if mode in ["vector", "hybrid", "both"]:
        with console.status("[bold green]Vectorizing query...[/bold green]"):
            embeddings_tensor = embedder.encode_single(query_text, is_query=True)
            query_vector = embeddings_tensor.cpu().numpy().tolist()[0]

    # 1. ベクトル検索
    if mode in ["vector", "both"]:
        with console.status("[bold green]Searching (Vector)...[/bold green]"):
            vector_results = client.search(query_vector, limit=top_k)
            display_results(vector_results, "Vector Search (Meaning)", "green")

    # 2. 全文検索（FTS）
    if mode in ["fts", "both"]:
        with console.status("[bold blue]Searching (FTS)...[/bold blue]"):
            fts_results = client.search_fts(query_text, limit=top_k)
            display_results(fts_results, "Full-Text Search (Keywords)", "blue")

    # 3. ハイブリッド検索（RRF + Rerank）
    if mode in ["hybrid", "both"]:
        with console.status("[bold magenta]Searching (Hybrid RRF + Rerank)...[/bold magenta]"):
            hybrid_results = client.search_hybrid_manual(query_text, query_vector, limit=top_k)
            display_results(hybrid_results, "Advanced Hybrid Search", "magenta")


async def main():
    setup_logging()
    
    parser = argparse.ArgumentParser(description="RAG Primitive Search Interface")
    parser.add_argument("query", nargs="*", help="Search query text")
    parser.add_argument("--mode", choices=["vector", "fts", "hybrid", "both"], default="both", help="Search mode")
    parser.add_argument("--top_k", type=int, default=3, help="Number of results to return")
    
    args = parser.parse_args()
    
    if args.query:
        query = " ".join(args.query)
    else:
        query = console.input("[bold yellow]Enter your question:[/bold yellow] ")

    if not query.strip():
        return

    await perform_hybrid_search(query, top_k=args.top_k, mode=args.mode)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Search interrupted.[/yellow]")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
