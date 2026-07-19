"""
課題28: 自律テスト・修復マルチエージェント
テストコード (test_target_code.py)

※このテストコードはエージェントに書き換えさせてはいけないわ！
テストを実行して、すべてのアサーションがパスするように target_code.py を修復させなさい。
"""
import pytest
from target_code import calculate_order_totals


def test_basic_order_calculation():
    """通常の注文が正しく計算されることのテスト"""
    orders = [
        {
            "order_id": "ORD-001",
            "customer": {"customer_id": "C-1", "membership": "Regular"},
            "items": [
                {"item_id": "I-1", "price": 100.0, "quantity": 2},
                {"item_id": "I-2", "price": 50.0, "quantity": 1}
            ]
        }
    ]
    result = calculate_order_totals(orders)
    assert result["total_revenue"] == 250.0
    assert result["processed_count"] == 1


def test_vip_discount_and_case_insensitivity():
    """VIP割引が正しく適用され、大文字小文字の表記揺れもカバーできていることのテスト"""
    orders = [
        {
            "order_id": "ORD-002",
            "customer": {"customer_id": "C-2", "membership": "VIP"}, # 大文字のVIP
            "items": [
                {"item_id": "I-1", "price": 100.0, "quantity": 2} # 合計200 -> 10%OFFで180.0
            ]
        },
        {
            "order_id": "ORD-003",
            "customer": {"customer_id": "C-3", "membership": "vip"}, # 小文字のvip
            "items": [
                {"item_id": "I-2", "price": 50.0, "quantity": 2} # 合計100 -> 10%OFFで90.0
            ]
        }
    ]
    result = calculate_order_totals(orders)
    # 合計: 180 + 90 = 270.0
    assert result["total_revenue"] == 270.0
    assert result["processed_count"] == 2


def test_string_price_casting():
    """priceが文字列で入ってきても適切にキャストして集計できることのテスト"""
    orders = [
        {
            "order_id": "ORD-004",
            "customer": {"customer_id": "C-4", "membership": "Regular"},
            "items": [
                {"item_id": "I-1", "price": "150.5", "quantity": 2}, # 文字列のfloat
                {"item_id": "I-2", "price": "200", "quantity": 1}    # 文字列のint
            ]
        }
    ]
    result = calculate_order_totals(orders)
    # 150.5 * 2 + 200 = 501.0
    assert result["total_revenue"] == 501.0
    assert result["processed_count"] == 1
