from pydantic import BaseModel


class YearsSchema(BaseModel):
    """
    Schema representing a time range for a dataset or indicator.

    Attributes:
        id (str): A unique identifier for the year range (e.g. "Senegal:net_use")
        start_year (int): The beginning year of the dataset
        end_year (int): The final year of the dataset
    """
    id: str
    start_year: int
    end_year: int
