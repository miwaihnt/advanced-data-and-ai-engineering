import unittest
from collections import deque
from typing import Any

class ErrorMonitor:
    def __init__(self, window_size_seconds: float = 60.0):
        """
        移動窓（ウィンドウ）のサイズ（秒）を設定し、初期化する。
        """
        self.window_size = window_size_seconds
        # 時間計算量アモルタイズド O(1) で両端の操作ができるように deque を採用
        self.timestamps = deque()

    def _purge_old_data(self, current_timestamp: float) -> None:
        """
        現在の時刻（current_timestamp）を基準に、窓外（[current_timestamp - window_size, current_timestamp] の外側）
        へはみ出した古いタイムスタンプをパージ（削除）する。
        """
        limit = current_timestamp - self.window_size
        # タイムスタンプは単調増加という前提があるため、左側（最も古いデータ）から順番にチェックして削除するだけでOK
        while self.timestamps and self.timestamps[0] < limit:
            self.timestamps.popleft()

    def record_error(self, timestamp: float) -> int:
        """
        エラーが発生したタイムスタンプ（timestamp）を記録し、
        現在の窓内（[timestamp - window_size_seconds, timestamp]）のエラー件数を返す。
        """
        # 1. 窓から外れた古いデータをパージ
        self._purge_old_data(timestamp)
        # 2. 新しいエラーを記録
        self.timestamps.append(timestamp)
        # 3. 現在の有効なエラー数を返す
        return len(self.timestamps)

    def get_error_count(self, current_timestamp: float) -> int:
        """
        新しいエラーを記録せず、現在のタイムスタンプ（current_timestamp）における
        窓内の有効なエラー件数を返す。
        """
        # 1. 窓から外れた古いデータをパージ
        self._purge_old_data(current_timestamp)
        # 2. 現在の有効なエラー数を返す
        return len(self.timestamps)


# ==========================================
# 動作検証用のユニットテスト
# ==========================================
class TestErrorMonitor(unittest.TestCase):
    def test_basic_window_flow(self):
        monitor = ErrorMonitor(window_size_seconds=60.0)

        # 1. 最初のエラーを記録（t=10.0） ➔ カウント1
        self.assertEqual(monitor.record_error(10.0), 1)

        # 2. 同一時刻に別のエラーが発生（t=10.0） ➔ カウント2
        self.assertEqual(monitor.record_error(10.0), 2)

        # 3. 30秒後にエラーが発生（t=40.0） ➔ カウント3
        self.assertEqual(monitor.record_error(40.0), 3)

        # 4. さらに30秒後にエラーが発生（t=70.0） ➔ ギリギリt=10.0も残ってカウント4
        self.assertEqual(monitor.record_error(70.0), 4)

        # 5. さらに0.1秒後にエラーが発生（t=70.1） ➔ t=10.0 の2件がパージされてカウント3
        self.assertEqual(monitor.record_error(70.1), 3)

    def test_get_error_count_without_recording(self):
        monitor = ErrorMonitor(window_size_seconds=60.0)

        monitor.record_error(10.0)
        monitor.record_error(20.0)
        monitor.record_error(30.0)

        # 記録なしでt=50.0時点でのエラー数を取得 ➔ カウント3
        self.assertEqual(monitor.get_error_count(50.0), 3)

        # 記録なしでt=75.0時点でのエラー数を取得 ➔ t=10.0がパージされてカウント2
        self.assertEqual(monitor.get_error_count(75.0), 2)

        # 記録なしでt=100.0時点でのエラー数を取得 ➔ すべてパージされてカウント0
        self.assertEqual(monitor.get_error_count(100.0), 0)

    def test_large_gap_and_empty_queue(self):
        monitor = ErrorMonitor(window_size_seconds=60.0)

        self.assertEqual(monitor.record_error(10.0), 1)
        
        # 1時間後にエラーが発生（t=3610.0）
        self.assertEqual(monitor.record_error(3610.0), 1)
        self.assertEqual(monitor.get_error_count(3700.0), 0)

if __name__ == '__main__':
    unittest.main()
