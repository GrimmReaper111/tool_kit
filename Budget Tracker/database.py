import os

import pandas as pd
from sqlalchemy import Column, Date, Float, Integer, String, create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database setup
DB_DIR = os.path.join(os.path.dirname(__file__), 'data')
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

DB_PATH = os.path.join(DB_DIR, 'expenses.db')
engine = create_engine(f'sqlite:///{DB_PATH}')
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

class Expense(Base):
    __tablename__ = 'expenses'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    category = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String)
    store = Column(String)
    place = Column(String)

class Income(Base):
    __tablename__ = 'income'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    source = Column(String, nullable=False)
    amount = Column(Float, nullable=False)


class Budget(Base):
    __tablename__ = 'budgets'
    id = Column(Integer, primary_key=True)
    category = Column(String, unique=True, nullable=False)
    monthly_limit = Column(Float, nullable=False)


class Setting(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)

# Migration: Check for missing columns in existing database
def migrate_db():
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('expenses')]
    
    with engine.connect() as conn:
        if 'store' not in columns:
            conn.execute(text("ALTER TABLE expenses ADD COLUMN store TEXT"))
            conn.commit()
        if 'place' not in columns:
            conn.execute(text("ALTER TABLE expenses ADD COLUMN place TEXT"))
            conn.commit()

migrate_db()

# Category Helpers
def get_categories():
    session = Session()
    try:
        cats = session.query(Category).all()
        if not cats:
            defaults = ["Food", "Transport", "Utilities", "Fun", "Healthcare"]
            for name in defaults:
                session.add(Category(name=name))
            session.commit()
            cats = session.query(Category).all()
        return [c.name for c in cats]
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def add_category(name):
    session = Session()
    try:
        clean_name = (name or "").strip()
        if not clean_name:
            return False
        if not session.query(Category).filter_by(name=clean_name).first():
            session.add(Category(name=clean_name))
            session.commit()
            return True
        return False
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def delete_category(name):
    session = Session()
    try:
        clean_name = (name or "").strip()
        if not clean_name:
            return False

        used_count = session.query(Expense).filter(Expense.category == clean_name).count()
        if used_count > 0:
            return False

        category = session.query(Category).filter(Category.name == clean_name).first()
        if not category:
            return False

        session.delete(category)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# Expense Helpers
def add_expense(date, category, amount, description, store=None, place=None):
    session = Session()
    try:
        new_expense = Expense(
            date=date,
            category=category,
            amount=amount,
            description=description,
            store=store,
            place=place,
        )
        session.add(new_expense)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_all_expenses():
    session = Session()
    try:
        return session.query(Expense).order_by(Expense.date.desc(), Expense.id.desc()).all()
    finally:
        session.close()

# Income Helpers
def add_income(date, source, amount):
    session = Session()
    try:
        new_income = Income(date=date, source=source, amount=amount)
        session.add(new_income)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_all_income():
    session = Session()
    try:
        return session.query(Income).order_by(Income.date.desc(), Income.id.desc()).all()
    finally:
        session.close()


def get_budgets():
    session = Session()
    try:
        return session.query(Budget).order_by(Budget.category.asc()).all()
    finally:
        session.close()


def set_budget(category, monthly_limit):
    session = Session()
    try:
        clean_category = (category or "").strip()
        if not clean_category:
            return False

        budget = session.query(Budget).filter(Budget.category == clean_category).first()
        if budget:
            budget.monthly_limit = float(monthly_limit)
        else:
            session.add(Budget(category=clean_category, monthly_limit=float(monthly_limit)))
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def delete_budget(category):
    session = Session()
    try:
        clean_category = (category or "").strip()
        budget = session.query(Budget).filter(Budget.category == clean_category).first()
        if not budget:
            return False
        session.delete(budget)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_setting(key, default=None):
    session = Session()
    try:
        row = session.query(Setting).filter(Setting.key == key).first()
        if not row:
            return default
        return row.value
    finally:
        session.close()


def set_setting(key, value):
    session = Session()
    try:
        clean_key = (key or "").strip()
        if not clean_key:
            return False

        row = session.query(Setting).filter(Setting.key == clean_key).first()
        if row:
            row.value = str(value)
        else:
            session.add(Setting(key=clean_key, value=str(value)))
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _normalize_date(value):
    if pd.isna(value):
        return None
    ts = pd.to_datetime(value, errors='coerce')
    if pd.isna(ts):
        return None
    return ts.date()


def _normalize_optional(value):
    if pd.isna(value):
        return None
    text_value = str(value).strip()
    return text_value if text_value else None


def _safe_float(value, fallback=0.0):
    if pd.isna(value):
        return fallback
    return float(value)

def update_expenses_from_df(df):
    session = Session()
    try:
        existing_expenses = {e.id: e for e in session.query(Expense).all()}
        incoming_ids = set()

        for _, row in df.iterrows():
            eid = row.get('id')
            normalized_date = _normalize_date(row.get('date'))
            category = _normalize_optional(row.get('category'))

            if not normalized_date or not category:
                continue

            amount = _safe_float(row.get('amount'))
            description = _normalize_optional(row.get('description'))
            store = _normalize_optional(row.get('store'))
            place = _normalize_optional(row.get('place'))

            if pd.notna(eid) and int(eid) in existing_expenses:
                expense_id = int(eid)
                incoming_ids.add(expense_id)
                expense = existing_expenses[expense_id]
                expense.date = normalized_date
                expense.category = category
                expense.amount = amount
                expense.description = description
                expense.store = store
                expense.place = place
            else:
                new_expense = Expense(
                    date=normalized_date,
                    category=category,
                    amount=amount,
                    description=description,
                    store=store,
                    place=place,
                )
                session.add(new_expense)

        ids_to_delete = set(existing_expenses.keys()) - incoming_ids
        if ids_to_delete:
            session.query(Expense).filter(Expense.id.in_(ids_to_delete)).delete(synchronize_session=False)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def update_income_from_df(df):
    session = Session()
    try:
        existing_income = {i.id: i for i in session.query(Income).all()}
        incoming_ids = set()

        for _, row in df.iterrows():
            iid = row.get('id')
            normalized_date = _normalize_date(row.get('date'))
            source = _normalize_optional(row.get('source'))

            if not normalized_date or not source:
                continue

            amount = _safe_float(row.get('amount'))

            if pd.notna(iid) and int(iid) in existing_income:
                income_id = int(iid)
                incoming_ids.add(income_id)
                income = existing_income[income_id]
                income.date = normalized_date
                income.source = source
                income.amount = amount
            else:
                new_income = Income(date=normalized_date, source=source, amount=amount)
                session.add(new_income)

        ids_to_delete = set(existing_income.keys()) - incoming_ids
        if ids_to_delete:
            session.query(Income).filter(Income.id.in_(ids_to_delete)).delete(synchronize_session=False)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
