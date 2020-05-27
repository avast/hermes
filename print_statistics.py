"""
This module prints statistics from the database.
Note: Run only using script statistics.sh!
Author: Silvie Chlupová
Date    Created: 04/26/2020
"""

from salmon.salmondb import get_statistics
from prettytable import PrettyTable
from datetime import datetime


def get_name(checkpoint_id):
    """Function returns the name of the checkpoint (e.g. email with attachment).

    Args:
        checkpoint_id (id): Unique checkpoint_id in the database.

    Returns:
        str: Required checkpoint name.
    """
    switch = {
        1: "email with attachment",
        2: "recipient used in TestMail",
        3: "similar email in MaybeTestMail",
        4: "similar email in TestMail",
        5: "relayed emails",
        6: "password in body_plain",
        7: "password in subject",
        8: "password in body_html",
        9: "word test or testing in body_plain",
        10: "word test or testing in subject",
        11: "word test or testing in body_html",
        12: "email with links",
        13: "username in body_html",
        14: "username in subject",
        15: "username in body_plain",
        16: "username in body_plain without subject",
        17: "specific time",
        18: "honeypot IP in body_plain",
        19: "honeypot IP in subject",
        20: "honeypot IP in body_html",
        21: "many real-world words",
        22: "less real-world words",
        23: "email has topic",
    }
    return switch.get(checkpoint_id, None)


def print_statistics():
    """Function prints statistics from the database."""
    statistics = get_statistics()
    table = PrettyTable()
    table.field_names = ["name", "used", "created", "last modified"]
    for record in statistics:
        checkpoint_name = get_name(record.checkpoint_id)
        if checkpoint_name is not None:
            table.add_row(
                [
                    checkpoint_name,
                    record.counter,
                    datetime.fromtimestamp(record.created),
                    datetime.fromtimestamp(record.last_modified),
                ]
            )
    print(table)

print_statistics()
