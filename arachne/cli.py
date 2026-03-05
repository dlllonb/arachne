"""Command-line interface for Arachne."""

from arachne.engine import query


def main():
    """Entry point for the arachne command."""
    import sys
    user_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    response = query(user_input)
    print(response)


if __name__ == "__main__":
    main()

