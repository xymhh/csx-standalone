"""Unavailable host browser adapter; importing the search layer stays optional."""


class PlaywrightHelper:
    def action(self, *args, **kwargs):
        raise NotImplementedError("MoviePilot Playwright browser integration is unavailable")
