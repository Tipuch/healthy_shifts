from db import SQLModel, engine


def main():
    print("Hello from healthy-shifts!")
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    main()
