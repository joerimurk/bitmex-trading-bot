from datetime import datetime

from sqlalchemy import ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Orders(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(primary_key=True)
    quantity: Mapped[int]
    price: Mapped[float]
    timestamp: Mapped[datetime]

    def __repr__(self) -> str:
        return f"Orders(id={self.order_id}, quantity={self.quantity}, price={self.price}, timestamp={self.timestamp})"


class Balance(Base):
    __tablename__ = "balance"

    id: Mapped[str] = mapped_column(primary_key=True)
    balance_before: Mapped[float]
    balance_after: Mapped[float]
    timestamp: Mapped[datetime]
    sell_order_id = mapped_column(ForeignKey("orders.order_id"))

    def __repr__(self) -> str:
        return f"Balance(id={self.id}, balance_before={self.balance_before}, balance_after={self.balance_after}, timestamp={self.timestamp}, sell_order_id={self.sell_order_id})"
