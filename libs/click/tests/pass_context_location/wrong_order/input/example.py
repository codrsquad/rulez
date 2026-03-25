import click

@click.command()
@click.pass_context
@click.option('--name')
def cmd(ctx, name):
    pass
