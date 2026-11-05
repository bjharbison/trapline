"""Launch the local development server without enabling remote exposure."""

import uvicorn

from .config import Settings


def main() -> None:
    settings = Settings.from_env()
    uvicorn.run("trapline_api.app:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()
