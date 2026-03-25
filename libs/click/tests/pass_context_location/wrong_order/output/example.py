import click

@click.command()
@click.option('--name')
@click.pass_context
def cmd(ctx, name):
    pass
