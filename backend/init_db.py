
from app.database import Base, engine
from app import models  # noqa: F401


def init_db():
    Base.metadata.create_all(bind=engine)
    print("TrustVault database tables created successfully.")

    print("\nTables:")
    for table_name in Base.metadata.tables:
        print(f"- {table_name}")


if __name__ == "__main__":
    init_db()
