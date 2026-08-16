"""
Runner wrapper for rich output: matplotlib figures as base64 PNGs.

The user code is concatenated at module level into RUNNER_TEMPLATE
(indent-sensitive, same pattern as the challenge harness), so it runs
verbatim. After the user code finishes, any still-open matplotlib figure
is rendered to a PNG and the base64 payload is written to the real stdout
as the last line, prefixed by PYFLOW_IMAGES::

    PYFLOW_IMAGES::["<base64 png>", ...]

If matplotlib cannot be imported (e.g. it is not installed), the wrapper
degrades gracefully: the user code still runs at module level and only the
figure-collection epilogue is skipped. The engine then reports the run
with an empty images list instead of an error.

The marker is written to the original stdout captured before the user code
runs, and starts on its own line, so a user print without a trailing
newline cannot swallow it.
"""

import textwrap

USER_CODE_PLACEHOLDER = "# <USER_CODE_PLACEHOLDER>"
IMAGES_MARKER_PREFIX = "PYFLOW_IMAGES::"

RUNNER_TEMPLATE = textwrap.dedent(
    """\
    import base64, io, json, sys

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        _matplotlib_available = True
    except Exception:
        # The image feature is optional: never let a missing/broken
        # matplotlib take down the user's run.
        _matplotlib_available = False

    _original_stdout = sys.stdout

    # <USER_CODE_PLACEHOLDER>

    if _matplotlib_available:
        plt.ioff()
        _images = []
        for num in plt.get_fignums():
            fig = plt.figure(num)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight")
            _images.append(base64.b64encode(buf.getvalue()).decode("ascii"))
            plt.close(fig)

        if _images:
            _original_stdout.write("\\n" + "PYFLOW_IMAGES::" + json.dumps(_images) + "\\n")
    """
)


def build_rich_script(code: str) -> str:
    """Wrap user code in the runner template, keeping its indentation intact."""
    return RUNNER_TEMPLATE.replace(USER_CODE_PLACEHOLDER, code.rstrip("\n"))
