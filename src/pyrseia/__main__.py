from asyncio import run
from importlib import import_module
from inspect import getmodule

import typer

from . import close_client


def main(
    client_factory: str,
    invocation: str,
    interactive: bool = typer.Option(False, "--interactive", "-i"),
):
    """Invoke a client method and print the result."""
    client_factory_module, factory_name = client_factory.split(":")

    async def call():
        mod = import_module(client_factory_module)
        factory = getattr(mod, factory_name)

        invocation_parts = invocation.split("(")
        method = invocation_parts[0]
        args = [
            p.strip() for p in invocation_parts[1].split(")")[0].split(",")
        ]

        client = await factory()
        api_module = getmodule(client.__class__.__bases__[0])

        evald_args = [eval(arg, vars(api_module), {}) for arg in args]
        res = await getattr(client, method)(*evald_args)
        await close_client(client)
        if interactive:
            print("The invocation request is available as 'res'.")
            breakpoint()
        else:
            print(res)

    run(call())


if __name__ == "__main__":
    typer.run(main)
