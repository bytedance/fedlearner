# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

# Ref: https://github.com/pallets/flask-sqlalchemy/blob/main/src/flask_sqlalchemy/__init__.py
from typing import Optional

from math import ceil

from sqlalchemy import func
from sqlalchemy.orm import Query


class Pagination:

    def __init__(self, query: Query, page: int, page_size: int):
        """Constructor for pagination

        Args:
            query (Query): A SQLAlchemy query
            page (int): The selected page
            page_size (int): The number of items on each page
        """
        self.query = query
        self.page = page
        self.page_size = page_size
        self._total_of_items = None

    def get_number_of_items(self) -> int:
        """Get the total number of items in the query.

        Returns:
            The total of items from the original query.
        """
        if self._total_of_items is None:
            # A raw query without any WHERE clause will result in a SQL statement without FROM clause
            # Therefore, if there is not FROM clause detected, we use a subquery to count the items
            # Ref: https://stackoverflow.com/questions/12941416/how-to-count-rows-with-select-count-with-sqlalchemy#comment118672248_57934541 # pylint:disable=line-too-long
            # FYI: Even 1.4.35 did not resolve this issue
            if ' FROM ' not in str(self.query).upper():
                self._total_of_items = self.query.count()
            else:
                self._total_of_items = self.query.with_entities(func.count()).scalar()

        return self._total_of_items

    def get_items(self) -> iter:
        """Get a "page" of items.
        CAUTION: Returns all records if {self.page_size} is 0.

        Returns:
            An iterable contains {self.page_size} items on {self.page} page.
        """
        if self.page_size == 0:
            return self.query.all()
        return self.query.limit(self.page_size).offset((self.page - 1) * self.page_size).all()

    def get_number_of_pages(self) -> int:
        """Get the number of pages of the query according to the specified
        per_page value.
        CAUTION: Returns 1 if {self.page_size} is 0 and the query has records.

        Returns:
            The number of pages of all items from the original query.
        """
        if self.get_number_of_items() == 0:
            return 0
        if self.page_size == 0:
            return 1
        return int(ceil(self.get_number_of_items() / float(self.page_size)))

    def get_metadata(self) -> dict:
        """Get pagination metadata in a dictionary.

        Returns:
            A dictionary contains information needed for current page.
        """
        return {
            'current_page': self.page,
            'page_size': self.page_size,
            'total_pages': self.get_number_of_pages(),
            'total_items': self.get_number_of_items()
        }


def paginate(query: Query, page: Optional[int] = None, page_size: Optional[int] = None) -> Pagination:
    """Paginate a query.

    Check if page and page_size are valid and construct a new Pagination
    object by a SQLAlchemy Query.
    CAUTION: page starts at one

    Args:
        query (Query): Query to be paginated
        page (int): Page selected in pagination (page >= 0)
        page_size (int): Number of items on each page (page_size <= 100)

    Returns:
        A Pagination object contains the selected items and metadata.

    Raises:
        ValueError: page >= 1 and 0 <= page_size <= 100.
    """
    page = page or 1
    page_size = page_size or 0
    if not (page >= 1 and 0 <= page_size <= 100):
        raise ValueError('page should be positive and page_size ranges between 0 and 100')

    return Pagination(query, page, page_size)
