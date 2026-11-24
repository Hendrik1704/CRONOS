"""Read C++ sources of the external codes for the parameter list tests."""


def strip_cpp_comments(source):
    """Remove // and /* */ comments from C++ source, keeping string literals.

    Commented-out parameter reads must not count as parameters.
    """
    out = []
    i, n = 0, len(source)
    while i < n:
        c = source[i]
        if c in "\"'":
            j = i + 1
            while j < n and source[j] != c:
                j += 2 if source[j] == "\\" else 1
            out.append(source[i : j + 1])
            i = j + 1
        elif source.startswith("//", i):
            j = source.find("\n", i)
            i = n if j < 0 else j
        elif source.startswith("/*", i):
            j = source.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def read_cpp_sources(paths):
    """Return the concatenated sources without comments."""
    source = ""
    for path in sorted(paths):
        with open(path, errors="replace") as f:
            source += strip_cpp_comments(f.read())
    return source
