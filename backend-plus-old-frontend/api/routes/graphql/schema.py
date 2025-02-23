import strawberry
from typing import List

@strawberry.type
class Query:
    @strawberry.field
    def hello(self, name: str) -> str:
        return f"Hello, {name}!"

@strawberry.type
class Mutation:
    @strawberry.field
    def echo(self, message: str) -> str:
        return message

schema = strawberry.Schema(query=Query, mutation=Mutation)
