from db import engine, SQLModel


def main():
    print("Hello from healthy-shifts!")
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    main()
