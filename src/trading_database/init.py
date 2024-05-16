from sqlalchemy import create_engine
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Orders(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(primary_key=True)
    quantity: Mapped[str]
    price: Mapped[str]
    timestamp: Mapped[datetime]

    def __repr__(self) -> str:
        return f"Orders(id={self.order_id}, quantity={self.quantity}, price={self.quantity}, timestamp={self.timestamp})"


class Balance(Base):
    __tablename__ = "balance"

    id: Mapped[int] = mapped_column(primary_key=True)
    balance_before: Mapped[float]
    balance_after: Mapped[float]
    timestamp: Mapped[datetime]
    sell_order_id = mapped_column(ForeignKey("orders.order_id"))

    def __repr__(self) -> str:
        return f"Balance(id={self.id}, balance_before={self.balance_before}, balance_after={self.balance_after}, timestamp={self.timestamp}, sell_order_id={self.sell_order_id})"


if __name__ == "__main__":
    engine = create_engine("sqlite:///src/trading_database/trades.db", echo=True)
    Base.metadata.create_all(engine)
