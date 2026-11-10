#!/usr/bin/env python3
"""
Manage per-student Kibana credentials stored in an Excel workbook.

The workbook sheet must contain a header row (row 1) with an "Email" column.

  generate  Adds the columns "Password" and "Kibana User" (if missing) and fills
            empty cells: a random password per student and "<prefix><n>" as
            Kibana user (n = position of the student in the sheet, 1-based).
            Existing values are kept unless --regenerate-passwords is given.

  export    Reads "Kibana User" and "Password" and prints them as JSON
            ([{"username": ..., "password": ...}, ...]) for the Ansible playbook.
            A "Kibana User" that is just a number (e.g. 3) gets the prefix
            prepended (kibana_user3).

Usage:
    python kibana_credentials.py generate students.xlsx
    python kibana_credentials.py export students.xlsx
"""

import argparse
import json
import secrets
import sys

from copy import copy
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter, range_boundaries
from openpyxl.worksheet.table import TableColumn

EMAIL = "Email"
PASSWORD = "Password"
KIBANA_USER = "Kibana User"

LETTERS_DIGITS = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
SYMBOLS = "!#%+=-_"


class CredentialsError(Exception):
    pass


def generate_password(length=16):
    """Cryptographically random password with upper, lower, digit and symbol.

    The first character is alphanumeric so Excel never treats it as a formula.
    """
    while True:
        chars = [secrets.choice(LETTERS_DIGITS)]
        chars += [secrets.choice(LETTERS_DIGITS + SYMBOLS) for _ in range(length - 1)]
        pw = "".join(chars)
        if (any(c.isupper() for c in pw) and any(c.islower() for c in pw)
                and any(c.isdigit() for c in pw) and any(c in SYMBOLS for c in pw)):
            return pw


def open_sheet(path, sheet, data_only=False):
    try:
        wb = load_workbook(path, data_only=data_only)
    except FileNotFoundError:
        raise CredentialsError(f"File '{path}' not found")
    except Exception as e:  # invalid extension, corrupt file, ...
        raise CredentialsError(f"Cannot read '{path}' as Excel workbook: {e}")
    if sheet not in wb.sheetnames:
        raise CredentialsError(f"Sheet '{sheet}' not found in '{path}' (available: {', '.join(wb.sheetnames)})")
    return wb, wb[sheet]


def find_column(ws, header):
    """Return the 1-based column index of a header in row 1 (case-insensitive) or None."""
    for cell in ws[1]:
        if isinstance(cell.value, str) and cell.value.strip().lower() == header.lower():
            return cell.column
    return None


def require_column(ws, header):
    col = find_column(ws, header)
    if col is None:
        raise CredentialsError(f"Required column '{header}' not found in header row of sheet '{ws.title}'")
    return col


def ensure_column(ws, header, style_from):
    """Return the index of `header`, adding it in the first free column right of the headers if missing."""
    col = find_column(ws, header)
    if col is not None:
        return col
    last_header = max(c.column for c in ws[1] if c.value not in (None, ""))
    col = last_header + 1
    # Skip columns that already hold data further down (e.g. helper cells) to never overwrite them
    while any(ws.cell(row=r, column=col).value not in (None, "") for r in range(1, ws.max_row + 1)):
        col += 1
    cell = ws.cell(row=1, column=col, value=header)
    cell._style = copy(style_from._style)
    letter = cell.column_letter
    ws.column_dimensions[letter].width = max(ws.column_dimensions[letter].width or 0, 22)
    extend_table(ws, col, header)
    return col


def extend_table(ws, col, header):
    """If an Excel table ends right before `col`, grow it to include the new column."""
    for table in ws.tables.values():
        min_c, min_r, max_c, max_r = range_boundaries(table.ref)
        if min_r == 1 and max_c == col - 1:
            table.ref = f"{get_column_letter(min_c)}{min_r}:{get_column_letter(col)}{max_r}"
            if table.autoFilter is not None:
                table.autoFilter.ref = table.ref
            table.tableColumns.append(TableColumn(id=len(table.tableColumns) + 1, name=header))


def student_rows(ws, email_col):
    return [r for r in range(2, ws.max_row + 1)
            if str(ws.cell(row=r, column=email_col).value or "").strip()]


def set_text(cell, value):
    cell.value = value
    cell.data_type = "s"  # never interpret as formula


def generate(args):
    wb, ws = open_sheet(args.file, args.sheet)
    email_col = require_column(ws, EMAIL)
    pw_col = ensure_column(ws, PASSWORD, ws.cell(row=1, column=email_col))
    user_col = ensure_column(ws, KIBANA_USER, ws.cell(row=1, column=email_col))

    rows = student_rows(ws, email_col)
    created = 0
    for n, r in enumerate(rows, start=1):
        pw_cell = ws.cell(row=r, column=pw_col)
        if args.regenerate_passwords or not str(pw_cell.value or "").strip():
            set_text(pw_cell, generate_password())
            created += 1
        user_cell = ws.cell(row=r, column=user_col)
        if not str(user_cell.value or "").strip():
            set_text(user_cell, f"{args.prefix}{n}")

    wb.save(args.output or args.file)
    print(f"Done: {len(rows)} students, {created} password(s) generated -> {args.output or args.file}",
          file=sys.stderr)


def export(args):
    _, ws = open_sheet(args.file, args.sheet, data_only=True)
    email_col = require_column(ws, EMAIL)
    pw_col = require_column(ws, PASSWORD)
    user_col = require_column(ws, KIBANA_USER)

    users, seen = [], set()
    for r in student_rows(ws, email_col):
        user = ws.cell(row=r, column=user_col).value
        if isinstance(user, float) and user.is_integer():
            user = int(user)
        user = str(user if user is not None else "").strip()
        if user.isdigit():
            user = f"{args.prefix}{user}"
        password = str(ws.cell(row=r, column=pw_col).value or "")
        if not user or not password:
            raise CredentialsError(f"Row {r}: '{KIBANA_USER}' and '{PASSWORD}' must both be set (run 'generate' first)")
        if user in seen:
            raise CredentialsError(f"Row {r}: duplicate Kibana user '{user}'")
        seen.add(user)
        users.append({"username": user, "password": password})

    if not users:
        raise CredentialsError("No students found")
    print(json.dumps(users))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func, helptext in (("generate", generate, "add/fill Password and Kibana User columns"),
                                 ("export", export, "print Kibana User/Password as JSON")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("file", help="Excel workbook (.xlsx)")
        p.add_argument("--sheet", default="Contacts", help="Sheet name (default: Contacts)")
        p.add_argument("--prefix", default="kibana_user", help="Kibana user prefix (default: kibana_user)")
        p.set_defaults(func=func)
        if name == "generate":
            p.add_argument("-o", "--output", help="Write to this file instead of modifying the input in place")
            p.add_argument("--regenerate-passwords", action="store_true",
                           help="Overwrite existing passwords (default: only fill empty cells)")

    args = parser.parse_args()
    try:
        args.func(args)
    except CredentialsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
