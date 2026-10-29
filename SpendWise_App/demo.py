#Create local demo accounts on demand.
from getpass import getpass

from sqlmodel import Session, select

from .database import engine
from .models import UserDetails
from .utils.auth import get_password_hash


DEMO_ACCOUNTS = (
    ("admin@gmail.com", "admin"),
    ("account1@gmail.com", "user"),
    ("account2@gmail.com", "user"),
    ("account3@gmail.com", "user"),
    ("account4@gmail.com", "user"),
    ("account5@gmail.com", "user"),
)
MIN_DEMO_PASSWORD_LENGTH = 12


def seed_demo_accounts(password: str) -> tuple[int, int]:

    if len(password) < MIN_DEMO_PASSWORD_LENGTH:
        raise ValueError(
            f"Use a demo password with at least {MIN_DEMO_PASSWORD_LENGTH} characters."
        )

    password_hash = get_password_hash(password)
    created = 0
    skipped = 0

    with Session(engine) as session:
        for email, user_type in DEMO_ACCOUNTS:
            statement = select(UserDetails).where(UserDetails.Email == email)
            if session.exec(statement).first():
                skipped += 1
                continue

            session.add(
                UserDetails(
                    Email=email,
                    HashedPassword=password_hash,
                    UserType=user_type,
                    Active=True,
                    EmailVerified=True,
                )
            )
            created += 1

        session.commit()

    return created, skipped


def main() -> None:
    print("This creates demo accounts in the database configured by your local .env.")
    print("Use only with a disposable local database and a temporary password.")
    if input('Type "SEED DEMO" to continue: ').strip() != "SEED DEMO":
        print("Cancelled; no demo accounts were created.")
        return

    password = getpass("Enter a demo password (12 or more characters): ")
    confirmation = getpass("Confirm the demo password: ")
    if password != confirmation:
        print("Passwords did not match; no demo accounts were created.")
        return

    try:
        created, skipped = seed_demo_accounts(password)
    except ValueError as error:
        print(f"{error} No demo accounts were created.")
        return

    print(f"Demo seeding finished: {created} account(s) created, {skipped} existing account(s) skipped.")


if __name__ == "__main__":
    main()
