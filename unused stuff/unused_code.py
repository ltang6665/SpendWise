#CALCULATIONS.PY DEMO CODE 

# ─────────────────────────────────────────────
# DEMO
# ─────────────────────────────────────────────

# --- PIR Demo ---
basket = [
    {"name": "Rice (5kg)",    "base_price": 8.00,  "current_price": 8.80,  "weight": 40},
    {"name": "Transport",     "base_price": 90.00, "current_price": 95.00, "weight": 90},
    {"name": "Groceries",     "base_price": 200.0, "current_price": 215.0, "weight": 200},
    {"name": "Dining out",    "base_price": 150.0, "current_price": 160.0, "weight": 150},
]
pir = calculate_pir(basket)
print(f"Personal Inflation Rate : {pir:.2f}%")

# --- Forecast Demo ---
past_spending = [1800, 1950, 1870]           # last 3 months
monthly_inflation = 0.005                    # 0.5% per month
forecast = calculate_forecast(past_spending, monthly_inflation, months_ahead=6)
print("\n6-Month Spending Forecast:")
for i, amount in enumerate(forecast, 1):
    print(f"  Month {i}: ${amount:.2f}")


# class UserSettingsBase(SQLModel):
#     UserId: int = Field(foreign_key="user_details.id", unique=True, index=True)
#     EmailOrPhone: Optional[str] = None
#     MonthlyIncome: float = Field(default=0.0, ge=0)
#     HouseholdSize: int = Field(default=1, ge=1)
#     TransportationType: TransportationTypeEnum = Field(default(TransportationTypeEnum.public))
#     MonthlyTransportSpending: float = Field(default=0.0, ge=0)
#     MonthlyUtilityBill: float = Field(default=0.0, ge=0)
#     PriceIncreaseAlerts: bool = True
#     BudgetThresholdAlerts: bool = True
#     AlertThreshold: int = Field(default=80, ge=1, le=100)


class UserMonthly(SQLModel):
    income: int
    HouseholdSize: int
    TransportType: str
    TransportCost: int
    utilities: int 

class MonthlyDB(UserMonthly):
    __tablename__ = "user_Monthly" # type: ignore
    # user_id relationship column?
    id: int | None = Field(default=None, primary_key=True)
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )

class UserAlerts(SQLModel):
    PriceIncrease: bool = False
    BudgetThreshold: bool = False
    AlertThreshold: int

class AlertsDB(UserAlerts):
    __tablename__ = "user_alerts" # type: ignore
    # user_id relationship column?
    id: int | None = Field(default=None, primary_key=True)
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )

settings = UserSettingsDB(
        UserId=user_id,
        Email=email,
        MonthlyIncome=0.0,
        HouseholdSize=1,
        #TransportationType=TransportationEnum.public,
        TransportationType=TransportationTypeEnum.public,
        MonthlyTransportSpending=0.0,
        MonthlyUtilityBill=0.0,
        PriceIncreaseAlerts=True,
        BudgetThresholdAlerts=True,
        AlertThreshold=80,
    )


"""@router.get("/{user_id}/previous-expenses", response_model=List[PreviousExpenseResponse])
def get_previous_expenses(user_id: int, db: Session = Depends(get_db)):

    Load previous expenses table.

    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)

    rows = (
        db.query(PreviousExpense)
        .filter(PreviousExpense.settings_id == settings.id)
        .order_by(PreviousExpense.month.desc())
        .all()
    )
    return rows"""

class UserSettingsUpdate(SQLModel):
    EmailOrPhone: Optional[str] = None
    MonthlyIncome: Optional[float] = Field(default=None, ge=0)
    HouseholdSize: Optional[int] = Field(default=None, ge=1)
    TransportationType: Optional[TransportationTypeEnum] = None
    MonthlyTransportSpending: Optional[float] = Field(default=None, ge=0)
    MonthlyUtilityBill: Optional[float] = Field(default=None, ge=0)
    PriceIncreaseAlerts: Optional[bool] = None
    BudgetThresholdAlerts: Optional[bool] = None
    AlertThreshold: Optional[int] = Field(default=None, ge=1, le=100)


#QUICK SETUP OPTION
@router.put("/{user_id}/quick-setup", response_model=UserSettingsRead)
def quick_setup(user_id: int, payload: QuickSetup, db: SessionDependency):
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)

    settings.MonthlyIncome = payload.MonthlyIncome
    if payload.Email is not None:
        settings.Email = payload.Email

    settings.SetupMode = "quick"
    settings.SetupCompleted = True

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings

class PreviousExpenseDB(PreviousExpense, table=True):
    __tablename__ = "previous_expenses" # type: ignore
    id: int | None = Field(default=None, primary_key=True)
    #UserId: int = Field(foreign_key = "user_details.id")
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )    
    SettingsId: int = Field(
        foreign_key="user_settings.id", 
        ondelete="CASCADE", 
        nullable=False, 
        index=True
    )
    
    Settings: Optional["UserSettingsDB"] = Relationship(back_populates="PreviousExpenses")

# for importing previous expenses and saving to db
@router.put("/{user_id}/previous-expenses", response_model=list[PreviousExpense]) # no need response model?
def save_previous_expenses(
    user_id: int,
    payload: AllPreviousExpenses,
    db: SessionDependency
):

    try:
        # Delete existing rows using SQLModel delete statement
        statement = delete(PreviousExpenseDB).where(PreviousExpenseDB.SettingsId == settings.id)
        db.exec(statement)

        new_rows = []
        for row_data in payload.AllExpenseRows:
            # Create new record using PascalCase fields
            record = PreviousExpenseDB(
                **row_data.model_dump(), SettingsId=settings.id 
            )
            db.add(record)
            new_rows.append(record)

        db.commit()
        
        for row in new_rows:
            db.refresh(row)

        return new_rows

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save previous expenses."
        )

# for deleting past expenses that were already saved into the db
@router.delete("/{user_id}/previous-expenses/{expense_id}")
def delete_previous_expense(user_id: int, expense_id: int, db: SessionDependency):
    # Verify settings exist first
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found.")

    # Find the specific row
    statement = select(PreviousExpenseDB).where(
        PreviousExpenseDB.id == expense_id,
        PreviousExpenseDB.SettingsId == settings.id 
    )
    expense = db.exec(statement).first()

    if not expense:
        raise HTTPException(status_code=404, detail="Expense record not found.")

    try:
        db.delete(expense)
        db.commit()
        return {"success": True}
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Deletion failed.")


#to update (save) a user’s settings in the database.
@router.put("/{user_id}", response_model=UserSettingsRead) 
def save_settings(user_id: int, payload: UserSettingsUpdate, db: SessionDependency):
    """Updates user settings fields."""
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)

    try:
         # check how frontend handles the data input?
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(settings, key, value)
        
        settings.UpdatedAt = datetime.utcnow() # change 

        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save settings."
        )

#QUICK SETUP OPTION
@router.put("/{user_id}/quick-setup", response_model=UserSettingsRead)
def quick_setup(user_id: int, payload: QuickSetupPayload, db: SessionDependency):
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)

    settings.MonthlyIncome = payload.MonthlyIncome
    if payload.EmailOrPhone is not None:
        settings.EmailOrPhone = payload.EmailOrPhone

    settings.SetupMode = "quick"
    settings.SetupCompleted = True
    settings.UpdatedAt = datetime.utcnow()

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings

#DETAILED SETUP OPTION
@router.put("/{user_id}/detailed-setup", response_model=UserSettingsRead)
def detailed_setup(user_id: int, payload: UserSettingsUpdate, db: SessionDependency):
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(settings, key, value)

    settings.SetupMode = "detailed"
    settings.SetupCompleted = True
    settings.UpdatedAt = datetime.utcnow()

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings
    

class UserSettingsRead(SQLModel):
    id: int
    UserId: int
    EmailOrPhone: Optional[str]
    MonthlyIncome: float
    HouseholdSize: int
    TransportationType: TransportationTypeEnum
    MonthlyTransportSpending: float
    MonthlyUtilityBill: float
    PriceIncreaseAlerts: bool
    BudgetThresholdAlerts: bool
    AlertThreshold: int
    SetupMode: str
    SetupCompleted: bool
    CreatedAt: datetime
    UpdatedAt: datetime | None = None

# gets the settings of the user to be displaayed
@router.get("/{user_id}", response_model=UserSettings) 
def get_user_settings(user_id: int, db: SessionDependency):
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)
    return settings


def create_default_settings(db: Session, user_id: int) -> UserSettingsDB: #if not, create default settings for the user
    email = get_user_email(db, user_id)

    settings = UserSettingsDB(
        UserId=user_id,
        Email=email,
        # do not need to set default values
    )

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings
class FullSettingsResponse(UserSettingsRead):
    # Id: int
    # UserId: int
    # CreatedAt: datetime
    # UpdatedAt: datetime
    PreviousExpenses: list[PreviousExpense] = []


# add expenses for any type to be saved in the db
@router.post("/", response_model=ExpensesDB, status_code=status.HTTP_201_CREATED)
def add_expense(expense: UserExpenses, db: SessionDependency, current_user: CurrentUser):

    db_expense = ExpensesDB(**expense.model_dump(), user_id=current_user.id)
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense












