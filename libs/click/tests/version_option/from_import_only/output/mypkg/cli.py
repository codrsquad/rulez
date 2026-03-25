from click import group
from click import version_option


@group()
@version_option()
def main():
    pass
