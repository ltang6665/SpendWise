# ENUMS
from enum import Enum


class UserType(str, Enum):
    ADMIN = "admin"
    USER = "user"

class TransportationType(str, Enum):
    #DEFAULT = "default"
    BUS = "bus"
    TRAIN = "train"
    BIKE = "bike"
    WALKING = "walking"
    ELECTRIC = "electric"
    HYBRID = "hybrid"
    GASOLINE = "gasoline"
    TAXI = "taxi"
    PRIVATE_HIRE = "private_hire"  # Use underscores for readability

class CategoryType(str, Enum):
    DEFAULT = "default"
    FOOD = "food"
    TRANSPORT = "transport"
    UTILITIES = "utilities"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    HEALTHCARE = "healthcare"
    OTHER = "other"

class AlertTypes(str, Enum):
    BUDGET = "budget"
    PRICE_INCREASE = "price_increase"