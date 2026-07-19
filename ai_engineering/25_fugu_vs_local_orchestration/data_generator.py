import json
from typing import List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime

# ==========================================
# 1. Pydantic Schemas (The Target Contract)
# ==========================================

class OrderItem(BaseModel):
    item_id: str = Field(..., description="Unique identifier for the item")
    price: float = Field(..., gt=0, description="Price per unit, must be greater than 0")
    quantity: int = Field(..., gt=0, description="Quantity ordered, must be at least 1")

class Customer(BaseModel):
    customer_id: str = Field(..., description="Unique customer ID")
    email: EmailStr = Field(..., description="Valid email address of the customer")
    membership: str = Field(..., description="Membership type: 'VIP', 'Regular', or 'Guest'")

    @field_validator("membership")
    @classmethod
    def validate_membership(cls, v: str) -> str:
        allowed = {"VIP", "Regular", "Guest"}
        if v not in allowed:
            raise ValueError(f"Membership must be one of {allowed}")
        return v

class Order(BaseModel):
    order_id: str = Field(..., description="Unique order ID")
    customer: Customer = Field(..., description="Customer details")
    items: List[OrderItem] = Field(..., description="List of items in the order")
    total_amount: float = Field(..., description="Total order amount. Must match sum of (price * quantity) of all items")
    order_date: datetime = Field(..., description="Date and time of the order in ISO format")

    @field_validator("total_amount")
    @classmethod
    def validate_total_amount(cls, v: float, info) -> float:
        # Check if total matches items sum (allowing small float precision tolerances)
        items = info.data.get("items")
        if items:
            expected_total = sum(item.price * item.quantity for item in items)
            if abs(v - expected_total) > 0.01:
                raise ValueError(f"Total amount {v} does not match the sum of items {expected_total}")
        return v


# ==========================================
# 2. Corrupted Data Generators for Benchmark
# ==========================================

def get_test_cases() -> List[Dict[str, Any]]:
    """
    Returns a list of test cases representing various data pipeline issues.
    Each test case has:
    - name: Description of the test
    - corrupted_json: The raw broken string to be parsed
    - expected_error_type: The error we expect Pydantic to throw initially
    """
    return [
        {
            "name": "Case 0: Valid Data (Control)",
            "corrupted_json": json.dumps({
                "order_id": "ORD-1001",
                "customer": {
                    "customer_id": "CUST-99",
                    "email": "alice@example.com",
                    "membership": "VIP"
                },
                "items": [
                    {"item_id": "ITEM-A", "price": 15.50, "quantity": 2},
                    {"item_id": "ITEM-B", "price": 9.99, "quantity": 1}
                ],
                "total_amount": 40.99,
                "order_date": "2026-07-14T09:00:00Z"
            }),
            "expected_error_type": None
        },
        {
            "name": "Case 1: Severe Type Coercion Error",
            "corrupted_json": json.dumps({
                "order_id": "ORD-1002",
                "customer": {
                    "customer_id": "CUST-102",
                    "email": "bob@example.com",
                    "membership": "Regular"
                },
                "items": [
                    {"item_id": "ITEM-C", "price": "10.00 USD", "quantity": "two"} # String in float/int fields
                ],
                "total_amount": 20.00,
                "order_date": "2026-07-14T09:05:00Z"
            }),
            "expected_error_type": "type_error"
        },
        {
            "name": "Case 2: Field Mapping Drift",
            "corrupted_json": json.dumps({
                "ord_number": "ORD-1003", # Drift: order_id -> ord_number
                "cust_info": { # Drift: customer -> cust_info
                    "cust_id": "CUST-103", # Drift: customer_id -> cust_id
                    "email": "charlie@example.com",
                    "membership": "Guest"
                },
                "items": [
                    {"item_id": "ITEM-D", "price": 4.99, "qty": 3} # Drift: quantity -> qty
                ],
                "total_amount": 14.97,
                "order_date": "2026-07-14T09:10:00Z"
            }),
            "expected_error_type": "missing"
        },
        {
            "name": "Case 3: Validation Constraint Violations",
            "corrupted_json": json.dumps({
                "order_id": "ORD-1004",
                "customer": {
                    "customer_id": "CUST-104",
                    "email": "invalid_email_format", # Constraint: EmailStr
                    "membership": "regular_customer" # Constraint: VIP/Regular/Guest
                },
                "items": [
                    {"item_id": "ITEM-E", "price": -5.00, "quantity": 0} # Constraints: price > 0, quantity > 0
                ],
                "total_amount": 0.00,
                "order_date": "2026-07-14T09:15:00Z"
            }),
            "expected_error_type": "value_error"
        },
        {
            "name": "Case 4: Schema Flattened (Structural Drift)",
            "corrupted_json": json.dumps({
                "order_id": "ORD-1005",
                # Structural Drift: customer dictionary is completely missing, 
                # instead customer fields are flattened to the root level.
                "customer_id": "CUST-105",
                "customer_email": "dave@example.com",
                "customer_membership": "Guest",
                "items": [
                    {"item_id": "ITEM-F", "price": 50.00, "quantity": 1}
                ],
                "total_amount": 50.00,
                "order_date": "2026-07-14T09:20:00Z"
            }),
            "expected_error_type": "missing"
        },
        {
            "name": "Case 5: Business Logic Mismatch",
            "corrupted_json": json.dumps({
                "order_id": "ORD-1006",
                "customer": {
                    "customer_id": "CUST-106",
                    "email": "eve@example.com",
                    "membership": "VIP"
                },
                "items": [
                    {"item_id": "ITEM-G", "price": 10.00, "quantity": 1}
                ],
                "total_amount": 999.99, # Logic: Total 999.99 != 10.00 * 1
                "order_date": "2026-07-14T09:25:00Z"
            }),
            "expected_error_type": "value_error"
        },
        {
            "name": "Case 6: Complex Hierarchical & Validation",
            "corrupted_json": json.dumps({
                "order_id": "ORD-2005",
                "customer": {
                    "customer_id": "CUST-205",
                    "email": "invalid_user@example.invalid",
                    "membership": "vip"
                },
                "shipping_address": {
                    "street": "1-2-3 桜通り",
                    "city": "東京",
                    "postal_code": "100-0001"
                    # country missing
                },
                "payment_info": {
                    "card_number": "1234-5678-####-####",
                    "expiry": "2027/04"
                },
                "items": [
                    {"item_id": "ITEM-X", "price": "15.00 USD", "quantity": "two"},
                    {"item_id": "ITEM-Y", "price": 8.5, "quantity": 3}
                ],
                "tax_rate": "0.08",
                "order_date": "2026/07/14 09:05 +09:00"
            }),
            "expected_error_type": "complex"
        }
    ]


if __name__ == "__main__":
    # Test validator with Case 0
    cases = get_test_cases()
    print("Testing Case 0 validation...")
    try:
        ord_obj = Order.model_validate_json(cases[0]["corrupted_json"])
        print(f"Success! Parsed object: {ord_obj}")
    except Exception as e:
        print(f"Failed Case 0: {e}")

    print("\nTesting Case 1 validation (should fail)...")
    try:
        Order.model_validate_json(cases[1]["corrupted_json"])
        print("Success? (Should not happen)")
    except Exception as e:
        print(f"Expected Failure: {e}")
