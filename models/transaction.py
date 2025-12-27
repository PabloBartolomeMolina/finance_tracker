'''
    File Name: transaction.py
    Version: 2.0.0
    Date: 27/12/2025
    Author: Pablo Bartolomé Molina
    Description: Transaction data model for the finance tracker.
'''
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Transaction:
    """
    Represents a single financial transaction.
    
    Attributes:
        description: Brief description of the transaction
        amount: Transaction amount (positive for income, negative for expense)
        date: Transaction date (YYYY-MM-DD format or datetime object)
        category: Category name (e.g., "Salary", "Rent", "Food")
        id: Unique identifier (None if not yet saved to DB)
    """
    description: str
    amount: float
    date: str  # ISO format: YYYY-MM-DD
    category: str
    id: Optional[int] = None

    def __post_init__(self):
        """Validate transaction data after initialization."""
        if not self.description or not self.description.strip():
            raise ValueError("Description cannot be empty")
        if self.amount == 0:
            raise ValueError("Amount cannot be zero")
        if not self.category or not self.category.strip():
            raise ValueError("Category cannot be empty")
        # Validate date format (simple ISO check)
        try:
            datetime.fromisoformat(self.date)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid date format: {self.date}. Expected YYYY-MM-DD")

    def to_dict(self) -> dict:
        """Convert transaction to dictionary (useful for DB operations)."""
        return {
            "id": self.id,
            "description": self.description,
            "amount": self.amount,
            "date": self.date,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        """Create a Transaction instance from a dictionary."""
        return cls(
            description=data.get("description", ""),
            amount=data.get("amount", 0.0),
            date=data.get("date", ""),
            category=data.get("category", ""),
            id=data.get("id", None),
        )

    def __repr__(self) -> str:
        return f"Transaction(id={self.id}, desc='{self.description}', amount={self.amount}, date={self.date}, category='{self.category}')"
