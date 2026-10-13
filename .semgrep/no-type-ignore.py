from typing import cast

# ruleid: no-type-ignore
value: int = "text"  # type: ignore[assignment]
# ruleid: no-type-ignore
other: int = "text"  # type: ignore
# ruleid: no-type-ignore
third: int = "text"  #type:ignore[assignment]
# ok: no-type-ignore
# Sound: the loader only ever stores ints under this key.
fourth = cast(int, {"n": 1}["n"])
# ok: no-type-ignore
ignore_type = "type: ignored"
