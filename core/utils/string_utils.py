from re import sub


def snake(s: str) -> str:
    ## Replace hyphens with spaces
    s = s.replace('-', ' ')

    ## Handle PascalCase pattern
    s = sub('([A-Z][a-z]+)', r' \1', s)

    ## Handle sequences of uppercase letters
    s = sub('([A-Z]+)', r' \1', s)

    ## Split by whitespace and join with underscores
    return '_'.join(s.split()).lower()
