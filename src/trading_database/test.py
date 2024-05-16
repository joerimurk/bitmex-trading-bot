from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from init import Orders, Balance, Base

if __name__ == "__main__":

    engine = create_engine("sqlite:///app/trades.db")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    new_order = Orders(
        order_id="6543", quantity=10, price=3000.30, timestamp=datetime.now()
    )
    new_balance = Balance(
        id=12345,
        balance_before=0.01001,
        balance_after=0.01003,
        timestamp=datetime.now(),
        sell_order_id="111",
    )

    session.add(new_order)
    session.add(new_balance)

    session.commit()
