import logging
import json
import math
from typing import Generator, Any, Mapping
from pathlib import Path
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%{asctime}s - %(levelname)s - %(message)s'
    )
logger = logging.getLogger(__name__)

@dataclass
class TempLog:
    sensor_id: str
    temperature: int

    @classmethod
    def validate_input(cls, data:Mapping[str, Any]) -> "TempLog":
        """
        辞書データを受け取り、バリデーション・クレンジングを行ってインスタンスを返す
        """
        # 必須キーチェック
        for key in ["sensor_id", "temperature"]:
            if key not in data:
                raise ValueError(f"[Skip]:必須キー{key}がありません")

        try:
            temp = float(data["temperature"])
        except (ValueError, TypeError) as e:
            raise ValueError(f"[Skip]:temperature{data['temperature']}の型変換に失敗しました")
        if math.isnan(temp) or math.isinf(temp):
            raise ValueError(f"temperature {temp}は非数または無限大です")
        
        return cls(sensor_id=data["sensor_id"], temperature=data["temperature"])


def process_stream(stream_path:Path) -> list[dict[str, Any]]:
    res = []
    if not stream_path.exists:
        logger.error(f"ファイルが見つかりません")
        return res
    
    # ファイルの読み込み
    with open(stream_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip(): continue
            # validation
            try:
                # jsonとしてパース
                data = json.loads(line)
                # バリデーション
                valid_data = TempLog.validate_input(data)
                res.append(
                    {"sensor_id": valid_data.sensor_id, 
                     "temperature": valid_data.temperature
                })
            except json.JSONDecodeError as e:
                logger.warning(f"[Skip]: jsonのデコードに失敗しました。{i}行目{line}, 原因：{e}")
            except ValueError as e:
                logger.warning(f"[Skip]: 必須キーチェックに失敗しました。{i}行目{line}, 原因：{e}")
            except Exception as e:
                logger.error(f"[Skip]:想定外のエラーが発生。{i}行目、データ:{line}。原因:{e}")
    return res


def main():
    # テストファイパスの設定
    input_path = Path.cwd() / "input/input.jsonl"

    logger.info(f"処理を開始")
    res = process_stream(input_path)
    print("----結果-----")
    print(res)


if __name__ == '__main__':
    main()