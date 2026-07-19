"""
課題28: 自律テスト・修復マルチエージェント
バグが混入したターゲットコード (target_code.py)

このファイルは、エージェントが自律的に修正する対象よ。
初期状態ではいくつかのバグ（型エラー、計算ミス、表記揺れの考慮漏れ）が含まれているわ。
"""
from typing import List, Dict, Any


def calculate_order_totals(orders: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    与えられた注文データのリストから、全体の総売上（割引適用後）と
    処理された有効な注文の数を計算する関数。
    
    バグ情報:
    1. VIP割引（10% OFF）の計算が間違っている（割引額そのものになってしまっている）。
    2. price が文字列で入ってくる場合があり、キャストしないとエラーになる。
    3. membership の表記揺れ（"VIP", "vip"）に対応できていない。
    """
    total_revenue = 0.0
    processed_count = 0

    for order in orders:
        items = order.get("items", [])
        customer = order.get("customer", {})
        membership = customer.get("membership", "Guest")

        # 注文内の各商品の金額を集計
        order_total = 0.0
        for item in items:
            price = item.get("price", 0.0)
            quantity = item.get("quantity", 1)
            # BUG: priceが文字列の場合にTypeErrorになる可能性があるわよ
            order_total += price * quantity

        # BUG: membership の表記揺れ（"VIP" と "vip"）を考慮していないわ
        if membership == "VIP":
            # BUG: 10%割引（0.9倍）のつもりが、0.1倍（割引額そのもの）になっているわよ！
            order_total = order_total * 0.1

        total_revenue += order_total
        processed_count += 1

    return {
        "total_revenue": total_revenue,
        "processed_count": processed_count
    }
