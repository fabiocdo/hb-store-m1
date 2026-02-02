class DbUpdaterUtils:
    """
    Utilities for updating and reading the store database.
    """

    def update_db(self):
        """
        Update the database with the latest indexed data.
        """
        raise NotImplementedError("update_db is not implemented yet")

    def read_db(self):
        """
        Read data from the database.
        """
        raise NotImplementedError("read_db is not implemented yet")
