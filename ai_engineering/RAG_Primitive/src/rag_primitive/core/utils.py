import itertools
import logging
from typing import Generator, Iterable, List
from sudachipy import dictionary, tokenizer

logger = logging.getLogger(__name__)


def batch_iterator(iterable: Iterable, batch_size: int) -> Generator[List, None, None]:
    """
    イテレータから指定されたバッチサイズごとにデータを束ねて yield する。
    itertools.islice を使うことで、余計なメモリコピーを最小限に抑える。
    """
    it = iter(iterable)
    while True:
        batch = list(itertools.islice(it, batch_size))
        if not batch:
            break
        yield batch


class JapaneseTokenizer:
    """
    日本語の分かち書きを担当するシングルトン・クラスよ。
    初期化（辞書ロード）のコストを最小限に抑えるための工夫が詰まってるわ。
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.info("Initializing SudachiPy dictionary (Singleton)...")
            cls._instance.sudachi_dict = dictionary.Dictionary()
            cls._instance.tokenizer = cls._instance.sudachi_dict.create()
            cls._instance.mode = tokenizer.Tokenizer.SplitMode.C
            # 無視したい品詞（ストップワード相当）の定義よ
            cls._instance.stop_pos = {"助詞", "助動詞", "記号", "空白"}
        return cls._instance

    def tokenize(self, text: str, filter_stop_words: bool = True) -> str:
        """
        テキストを分かち書きして、スペース区切りの文字列を返すわ。
        filter_stop_words=True にすると、助詞や記号を省いてキーワードの純度を高めるの。
        """
        if not text:
            return ""

        tokens = self.tokenizer.tokenize(text, self.mode)
        
        result = []
        for m in tokens:
            # 品詞（part_of_speech）の第一分類でフィルタリングするわ
            pos = m.part_of_speech()[0]
            if filter_stop_words and pos in self.stop_pos:
                continue
            result.append(m.surface())
            
        return " ".join(result)