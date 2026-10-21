"""The two ways a play-release step ends without finishing. Shared by release.py and play_api.py."""


class Stop(Exception):
    """A step that cannot go on: what failed, why, and the fix. The step is marked ⛔."""

    def __init__(self, what: str, why: str, fix: str):
        super().__init__(what)
        self.what, self.why, self.fix = what, why, fix


class Wait(Exception):
    """A step that waits on the operator (a manual step, or a go). The step is marked ◐."""

    def __init__(self, guide: str):
        super().__init__(guide)
        self.guide = guide
