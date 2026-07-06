import hashlib
import logging
from typing import Generator, List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sudachipy import dictionary, tokenizer

from rag_primitive.core.config import settings
from rag_primitive.core.utils import JapaneseTokenizer # 🚀 これを使うわよ！
from rag_primitive.schemas.speech import MeetingRecord, SpeechRecord
from rag_primitive.schemas.chunk import Chunk

logger = logging.getLogger(__name__)


class SpeechChunker:
    """
    国会会議録の発言データを、RAGに最適なサイズにチャンキングする。
    """

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        # 日本語に特化したセパレータの優先順位
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "、", " ", ""],
            add_start_index=True,
        )
        
        # トークナイザーを準備しておくわ
        self.tokenizer = JapaneseTokenizer()

    def generate_chunks(self, meeting: MeetingRecord) -> Generator[Chunk, None, None]:
        """
        1つの会議録（MeetingRecord）から全発言を抽出し、チャンク化して yield する。
        """
        for speech in meeting.speech_records:
            texts = self.splitter.split_text(speech.speech)
            
            for i, text in enumerate(texts):
                # 🚀 共通のトークナイザーを使って分かち書きよ！
                tokenized_text = self.tokenizer.tokenize(text)

                # チャンク内容に基づいてユニークなID（MD5）を生成
                hasher = hashlib.md5()
                hasher.update(f"{meeting.issue_id}{speech.speech_id}{text}".encode("utf-8"))
                chunk_id = hasher.hexdigest()

                yield Chunk(
                    chunk_id=chunk_id,
                    speech_id=speech.speech_id,
                    content=text,
                    content_tokenized=tokenized_text,
                    chunk_index=i,
                    speaker=speech.speaker,
                    date=meeting.date,
                    meeting_name=meeting.name_of_meeting
                )

    def process_batch(self, meetings: List[MeetingRecord]) -> List[Chunk]:
        """
        複数の会議録をまとめてバッチ処理する。
        """
        all_chunks = []
        for meeting in meetings:
            all_chunks.extend(list(self.generate_chunks(meeting)))
        return all_chunks
