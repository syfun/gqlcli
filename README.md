# gqlcli

Auto-generate GraphQL Type, Resolver and Query.


## Installation

`pip install gqlcli`

## TODO
- [ ] more rule for client command
- [x] support schema directory

## Usage

```shell script
Usage: gqlcli [OPTIONS] COMMAND [ARGS]...

Options:
  -f, --file TEXT  graphql sdl file, file extension may be .gql or .graphql
  --help           Show this message and exit.

Commands:
  all  Generate all schema types
  c    Generate client query
  fr   Generate field resolver.
  postman  Export all client query to postman.
  pt   Print type definition
  t    Generate one type
  tr   Generate type resolver
```

> `-f` option will auto find sdl file with `.gql` or `.graphql` extension in current dir.
>
> `gqlcli -p schema.graphql` same with `gqlcli`

GraphQL schema example:

```graphql
enum Episode { NEWHOPE, EMPIRE, JEDI }

interface Character {
  id: String!
  name: String
  friends: [Character]
  appearsIn: [Episode]
}

type Human implements Character {
  id: String!
  name: String
  friends: [Character]
  appearsIn: [Episode]
  homePlanet: String
}

type Droid implements Character {
  id: String!
  name: String
  friends: [Character]
  appearsIn: [Episode]
  primaryFunction: String
}

type Query {
  hero(episode: Episode): Character
  human(id: String!): Human
  droid(id: String!): Droid
}
```

### all

`all` command can generate all schema types, based on default class, dataclass or pydantic, default is pydantic.

`gqlcli all --kind pydantic`

```python
from enum import Enum
from typing import Any, Dict, List, NewType, Optional, Text, Union

from gql import enum_type, type_resolver
from pydantic import BaseModel

ID = NewType('ID', Text)


@enum_type
class Episode(Enum):
   NEWHOPE = 1
   EMPIRE = 2
   JEDI = 3


class Character(BaseModel):
    id: Text
    name: Optional[Text]
    friends: Optional[List[Optional['Character']]]
    appears_in: Optional[List[Optional[Episode]]]


class Human(Character):
    id: Text
    name: Optional[Text]
    friends: Optional[List[Optional['Character']]]
    appears_in: Optional[List[Optional[Episode]]]
    home_planet: Optional[Text]


class Droid(Character):
    id: Text
    name: Optional[Text]
    friends: Optional[List[Optional['Character']]]
    appears_in: Optional[List[Optional[Episode]]]
    primary_function: Optional[Text]


@type_resolver('Character')
def resolve_character_type(obj, info, type_):
    if isinstance(obj, Human):
        return 'Human'
    if isinstance(obj, Droid):
        return 'Droid'
    return None
```

> for `gql` package, please see [python-gql](https://github.com/syfun/python-gql) for detail.

## client

`c` command generate query string.

`gqlcli c hero`

```graphql
query hero($episode: Episode) {
  hero(episode: $episode) {
    id
    name
    friends
    appearsIn
  }
}
```

## field resolver

`fr` command generate field resolver.

`gqlcli fr Query hero`

```python
@query
def hero(parent, info, episode: Optional[Episode]) -> Optional['Character']:
    pass
```

## type resolver

`tr` command generate type resolver.

`gqlcli tr Character`

```python
@type_resolver('Character')
def resolve_character_type(obj, info, type_):
    if isinstance(obj, Human):
	 return 'Human'
    if isinstance(obj, Droid):
	 return 'Droid'
    return None
```

## type

`t` command generate given type.

`gqlcli c Character`

```python
class Character(BaseModel):
    id: Text
    name: Optional[Text]
    friends: Optional[List[Optional['Character']]]
    appears_in: Optional[List[Optional[Episode]]]
```

## print

`pt` command print type definition.

`gqlcli pt Character`

```graphql
interface Character {
  id: String!
  name: String
  friends: [Character]
  appearsIn: [Episode]
}
```

## postman

Generate a postman collection.

Example:

```
gqlcli -p ./schema.graphql  postman -H X-Authenticated-Scope:authenticated -H X-Authenticated-Userid:"{\"id\": \"{{USER}}\", \"meta\": {\"company_id\": {{COMPANY}}, \"is_superuser\": {{SUPERUSER}}}}" -H Authorization:"Token {{TOKEN}}" example
```