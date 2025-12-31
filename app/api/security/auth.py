from pydantic import BaseModel


class User(BaseModel):
    oid: str = "local-user"
    name: str = "Local User"


async def validate_authenticated() -> User:
    """
    Placeholder auth for local development.
    """
    return User()
