#!/usr/bin/env python3
"""
Hardcover Want-to-Read to List Converter

Converts want-to-read books from Hardcover reading status to a list format
that can be imported by Readarr.
"""

import argparse
import os
import sys
import time
from typing import Dict, List, Optional, Set

import requests
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Hardcover GraphQL API endpoint
API_ENDPOINT = "https://api.hardcover.app/v1/graphql"

# Reading status mappings
STATUS_MAP = {
    "want-to-read": {"id": 1, "name": "want-to-read", "description": "Books I want to read"},
    "currently-reading": {"id": 2, "name": "currently-reading", "description": "Books I'm currently reading"},
    "read": {"id": 3, "name": "read", "description": "Books I've read"},
    "did-not-finish": {"id": 4, "name": "did-not-finish", "description": "Books I did not finish"},
}


class HardcoverClient:
    """Client for interacting with the Hardcover GraphQL API."""

    def __init__(self, api_key: str):
        """
        Initialize the Hardcover client.

        Args:
            api_key: Hardcover API key for authentication
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
        }

    def _make_request(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """
        Make a GraphQL request to the Hardcover API.

        Args:
            query: GraphQL query or mutation string
            variables: Optional variables for the query

        Returns:
            Response data dictionary

        Raises:
            Exception: If the request fails or returns errors
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = requests.post(
                API_ENDPOINT, json=payload, headers=self.headers, timeout=30
            )
            response.raise_for_status()

            data = response.json()

            if "errors" in data:
                error_messages = [err.get("message", str(err)) for err in data["errors"]]
                raise Exception(f"GraphQL errors: {', '.join(error_messages)}")

            return data.get("data", {})

        except requests.exceptions.HTTPError as e:
            if response.status_code in (401, 403):
                raise Exception(
                    "Authentication failed. Please check your API key."
                ) from e
            raise Exception(f"HTTP error: {e}") from e
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {e}") from e

    def get_user_info(self) -> Dict:
        """
        Fetch authenticated user's information.

        Returns:
            User dictionary with id, username, and name
        """
        query = """
        query {
          me {
            id
            username
            name
          }
        }
        """

        data = self._make_request(query)

        # The API returns "me" as a list with one element
        me_data = data.get("me", [])
        if me_data and len(me_data) > 0:
            return me_data[0]
        else:
            return {}

    def get_books_by_status(self, status_id: int) -> List[Dict]:
        """
        Fetch all books with a specific reading status for the authenticated user.

        Args:
            status_id: Reading status ID (1=want-to-read, 2=currently-reading, 3=read, 4=did-not-finish)

        Returns:
            List of book dictionaries with id and title
        """
        query = """
        query GetBooksByStatus($status_id: Int!) {
          me {
            user_books(where: {status_id: {_eq: $status_id}}) {
              book {
                id
                title
              }
            }
          }
        }
        """

        variables = {"status_id": status_id}
        data = self._make_request(query, variables)

        # The API returns "me" as a list with one element
        me_data = data.get("me", [])
        if me_data and len(me_data) > 0:
            user_books = me_data[0].get("user_books", [])
        else:
            user_books = []

        return [ub["book"] for ub in user_books]

    def get_lists(self) -> List[Dict]:
        """
        Fetch all lists for the authenticated user.

        Returns:
            List of list dictionaries with id, name, slug, and books
        """
        query = """
        query {
          me {
            lists {
              id
              name
              slug
              list_books {
                book {
                  id
                }
              }
            }
          }
        }
        """

        data = self._make_request(query)

        # The API returns "me" as a list with one element
        me_data = data.get("me", [])
        if me_data and len(me_data) > 0:
            return me_data[0].get("lists", [])
        else:
            return []

    def create_list(self, name: str, description: str) -> Dict:
        """
        Create a new list.

        Args:
            name: Name of the list
            description: Description of the list

        Returns:
            Created list data with id
        """
        mutation = """
        mutation CreateList($name: String!, $description: String!) {
          insert_list(object: {
            name: $name,
            description: $description
          }) {
            id
          }
        }
        """

        variables = {
            "name": name,
            "description": description,
        }

        data = self._make_request(mutation, variables)
        return data.get("insert_list", {})

    def add_book_to_list(self, book_id: int, list_id: int, position: int) -> Dict:
        """
        Add a book to a list.

        Args:
            book_id: ID of the book to add
            list_id: ID of the list
            position: Position of the book in the list

        Returns:
            Created list_book data with id
        """
        mutation = """
        mutation AddBookToList($book_id: Int!, $list_id: Int!, $position: Int!) {
          insert_list_book(object: {
            book_id: $book_id,
            list_id: $list_id,
            position: $position
          }) {
            id
          }
        }
        """

        variables = {
            "book_id": book_id,
            "list_id": list_id,
            "position": position,
        }

        data = self._make_request(mutation, variables)
        return data.get("insert_list_book", {})


def find_list_by_name(lists: List[Dict], name: str) -> Optional[Dict]:
    """
    Find a list by name from a list of lists.

    Args:
        lists: List of list dictionaries
        name: Name to search for

    Returns:
        List dictionary if found, None otherwise
    """
    for list_item in lists:
        if list_item.get("name", "").lower() == name.lower():
            return list_item
    return None


def get_existing_book_ids(list_data: Dict) -> Set[int]:
    """
    Extract book IDs from a list.

    Args:
        list_data: List dictionary containing list_books

    Returns:
        Set of book IDs already in the list
    """
    book_ids = set()
    for list_book in list_data.get("list_books", []):
        book_id = list_book.get("book", {}).get("id")
        if book_id:
            book_ids.add(book_id)
    return book_ids


def main():
    """Main function to convert reading status books to lists."""
    parser = argparse.ArgumentParser(
        description="Convert Hardcover reading status books to lists for Readarr import"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Hardcover API key (can also use HARDCOVER_API_KEY env variable)",
    )
    parser.add_argument(
        "--status",
        type=str,
        choices=list(STATUS_MAP.keys()) + ["all"],
        help="Reading status to convert (default: interactive selection)",
    )
    args = parser.parse_args()

    # Get API key from argument or environment variable
    api_key = args.api_key or os.getenv("HARDCOVER_API_KEY")

    if not api_key:
        print("Error: API key is required.")
        print("Provide it via --api-key argument or HARDCOVER_API_KEY environment variable.")
        sys.exit(1)

    # Initialize client
    client = HardcoverClient(api_key)

    try:
        # Phase 0: Validate API key and get user info
        print("Validating API key and fetching user info...")
        user_info = client.get_user_info()

        if not user_info or "username" not in user_info:
            print("Error: Failed to fetch user information. Please check your API key.")
            sys.exit(1)

        username = user_info.get("username", "")
        user_name = user_info.get("name", username)
        print(f"Authenticated as: {user_name} (@{username})")

        # Determine which statuses to process
        if args.status:
            if args.status == "all":
                statuses_to_process = list(STATUS_MAP.keys())
            else:
                statuses_to_process = [args.status]
        else:
            # Interactive selection
            print("\nWhich reading statuses would you like to convert to lists?")
            print("Enter the numbers separated by spaces (e.g., '1 3' for want-to-read and read)")
            print("Or enter 'all' to convert all statuses:")
            for idx, (status_key, status_info) in enumerate(STATUS_MAP.items(), 1):
                print(f"  {idx}. {status_key} - {status_info['description']}")
            print(f"  {len(STATUS_MAP) + 1}. all - Convert all statuses")

            selection = input("\nYour selection: ").strip().lower()

            if selection == "all" or selection == str(len(STATUS_MAP) + 1):
                statuses_to_process = list(STATUS_MAP.keys())
            else:
                try:
                    selected_indices = [int(x) for x in selection.split()]
                    status_keys = list(STATUS_MAP.keys())
                    statuses_to_process = [
                        status_keys[idx - 1]
                        for idx in selected_indices
                        if 1 <= idx <= len(STATUS_MAP)
                    ]
                    if not statuses_to_process:
                        print("No valid selections. Exiting.")
                        sys.exit(0)
                except ValueError:
                    print("Invalid input. Exiting.")
                    sys.exit(1)

        print(f"\nProcessing {len(statuses_to_process)} status(es)...")

        # Track results across all statuses
        all_results = []

        # Process each selected status
        for status_key in statuses_to_process:
            status_info = STATUS_MAP[status_key]
            status_id = status_info["id"]
            list_name = status_info["name"]
            list_description = f"{status_info['description']} (auto-synced)"

            print(f"\n{'='*60}")
            print(f"Processing: {list_name}")
            print(f"{'='*60}")

            # Phase 1: Fetch books for this status
            print(f"Fetching your {list_name} books...")
            books = client.get_books_by_status(status_id)
            print(f"Found {len(books)} {list_name} books")

            if not books:
                print(f"No {list_name} books found. Skipping.")
                all_results.append({
                    "status": list_name,
                    "total": 0,
                    "added": 0,
                    "skipped": 0,
                    "failed": 0,
                    "list_url": None,
                })
                continue

            # Phase 2: Check for existing list
            print(f"Checking for existing '{list_name}' list...")
            lists = client.get_lists()
            existing_list = find_list_by_name(lists, list_name)

            if existing_list:
                print(f"List found! (ID: {existing_list['id']})")
                list_id = existing_list["id"]
                existing_book_ids = get_existing_book_ids(existing_list)
                print(f"List currently contains {len(existing_book_ids)} books")
            else:
                # Phase 3: Create new list
                print(f"List not found. Creating new '{list_name}' list...")
                new_list = client.create_list(
                    name=list_name,
                    description=list_description,
                )
                list_id = new_list["id"]
                existing_book_ids = set()
                existing_list = new_list
                print(f"List created! (ID: {list_id})")

            # Phase 4: Add books to list
            print(f"Adding books to list...")
            books_added = 0
            books_skipped = 0
            books_failed = 0

            # Start position after existing books
            position = len(existing_book_ids) + 1

            for book in books:
                book_id = book["id"]
                book_title = book["title"]

                if book_id in existing_book_ids:
                    books_skipped += 1
                    continue

                try:
                    client.add_book_to_list(book_id, list_id, position)
                    books_added += 1
                    position += 1
                    print(f"  [{books_added}] Added: {book_title}")

                    # Add a small delay to avoid rate limiting
                    time.sleep(0.5)
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "Too Many Requests" in error_msg:
                        print(
                            f"  Warning: Rate limited. Waiting 5 seconds before retrying..."
                        )
                        time.sleep(5)
                        # Retry once
                        try:
                            client.add_book_to_list(book_id, list_id, position)
                            books_added += 1
                            position += 1
                            print(f"  [{books_added}] Added: {book_title} (retried)")
                            time.sleep(0.5)
                        except Exception as retry_error:
                            print(
                                f"  Warning: Failed to add '{book_title}': {retry_error}"
                            )
                            books_failed += 1
                    else:
                        print(f"  Warning: Failed to add '{book_title}': {e}")
                        books_failed += 1

            # Generate list URL
            slug = existing_list.get("slug", list_name)
            list_url = f"https://hardcover.app/@{username}/lists/{slug}"

            # Store results
            all_results.append({
                "status": list_name,
                "total": len(books),
                "added": books_added,
                "skipped": books_skipped,
                "failed": books_failed,
                "list_url": list_url,
            })

            # Status summary
            print(f"\nStatus '{list_name}' complete!")
            print(f"  Total books: {len(books)}")
            print(f"  Added: {books_added}")
            print(f"  Skipped: {books_skipped}")
            if books_failed > 0:
                print(f"  Failed: {books_failed}")

        # Final summary
        print(f"\n{'='*60}")
        print("ALL COMPLETE!")
        print(f"{'='*60}")

        for result in all_results:
            if result["total"] > 0:
                print(f"\n{result['status'].upper()}:")
                print(f"  Total books: {result['total']}")
                print(f"  Added to list: {result['added']}")
                print(f"  Already in list: {result['skipped']}")
                if result["failed"] > 0:
                    print(f"  Failed: {result['failed']}")
                print(f"  List URL: {result['list_url']}")

        print("\n" + "=" * 60)
        print("You can now use these list URLs in Readarr's import lists!")

        total_failed = sum(r["failed"] for r in all_results)
        if total_failed > 0:
            print(
                f"\nNote: {total_failed} books failed to add across all lists due to API errors."
            )
            print("You can run this script again to add the remaining books.")

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
