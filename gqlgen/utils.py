import re


# From this response in Stackoverflow
# http://stackoverflow.com/a/1176023/1072990
def to_snake_case(name):
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def make_headers(headers: list):
    return [
        {'key': header.split(':', 1)[0], 'value': header.split(':', 1)[1], 'type': 'text'}
        for header in headers
    ]


def make_postman_request(name, query, headers):
    return {
        'name': name,
        'request': {
            'method': 'POST',
            'header': headers,
            'body': {
                'mode': 'graphql',
                'graphql': {'query': query, 'variables': ""},
                'options': {'graphql': {}},
            },
            'url': {
                'raw': '{{HOST}}' + f'?{name}',
                'host': ['{{HOST}}'],
                'query': [{'key': name, 'value': None}],
            },
        },
        'response': [],
    }
