"""Remove Co-authored-by trailers from stdin (for git filter-branch --msg-filter)."""
import sys

sys.stdout.write("".join(line for line in sys.stdin if not line.startswith("Co-authored-by:")))
