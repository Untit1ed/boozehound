from typing import Dict, Optional

from src.db_helper import DbHelper # Corrected import

from src.models.category import Category # Corrected import


class CategoryRepository:
    def __init__(self, db_helper: DbHelper):
        """
        Initialize the CategoryRepository with a DbHelper instance and load existing categories.

        :param db_helper: An instance of the DbHelper class.
        """
        self.db_helper = db_helper
        self.categories_map: Dict[int, Category] = self.load_categories()

    def load_categories(self) -> Dict[int, Category]:
        """
        Load all categories from the database into an in-memory dictionary.

        :return: A dictionary mapping Category objects to category IDs.
        """
        query = "SELECT name, bcl_id FROM categories"
        print('Loading categories from DB...', end='\r')
        categories = self.db_helper.execute_query(query)
        if not categories:
            return {}

        print(f'\x1b[2K\r{len(categories) if categories else 0} categories loaded.')

        return {bcl_id: Category(description=name, id=bcl_id) for name, bcl_id in categories}

    def get_or_add_category(
        self,
        category: Category,
        parent_category: Optional[Category] = None,
        grandparent_category: Optional[Category] = None
    ) -> int:
        """
        Retrieve the category ID if it exists in memory based on name and bcl_id;
        otherwise, insert the category into the database and return the new ID.
        If parent_category or grandparent_category are provided, ensure they exist and create them if necessary.

        :param category: The category object.
        :param parent_category: The parent category, if applicable.
        :param grandparent_category: The grandparent category, if applicable.
        :return: The ID of the category.
        """
        # Handle grandparent category if provided
        if grandparent_category:
            grandparent_category_id = self.get_or_add_category(grandparent_category)
            # Handle parent category if provided
            if parent_category:
                parent_category_id = self.get_or_add_category(parent_category, grandparent_category)
            else:
                parent_category_id = grandparent_category_id
        else:
            parent_category_id = None
            # Handle parent category if provided
            if parent_category:
                parent_category_id = self.get_or_add_category(parent_category)

        # Check if the category is already in memory
        if category.id in self.categories_map:
            return category.id

        # Insert category into the database
        insert_query = """
            INSERT INTO categories (name, parent_category_id, bcl_id)
            VALUES (%s, %s, %s);
        """
        new_category_id = self.db_helper.insert_query(
            insert_query, (category.description, parent_category_id, category.id))

        # Update the in-memory dictionary
        self.categories_map[category.id] = category

        print(f"{(category.description, parent_category_id, category.id)} category was inserted with id {new_category_id}.")

        return category.id
