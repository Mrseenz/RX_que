from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Table
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # e.g., 'doctor', 'pharmacist'

    prescriptions = relationship("Prescription", back_populates="doctor")

class Patient(Base):
    __tablename__ = 'patients'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    file_number = Column(String, unique=True, nullable=False)

    prescriptions = relationship("Prescription", back_populates="patient")

# Association Table for Prescription and Drug (Many-to-Many)
prescription_drug_association = Table('prescription_drug_association', Base.metadata,
    Column('prescription_id', Integer, ForeignKey('prescriptions.id'), primary_key=True),
    Column('drug_id', Integer, ForeignKey('drugs.id'), primary_key=True)
)

class Drug(Base):
    __tablename__ = 'drugs'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    strength = Column(String, nullable=False)
    instructions = Column(String, nullable=False)
    warnings = Column(String, nullable=False)

    prescriptions = relationship("Prescription", secondary=prescription_drug_association, back_populates="prescribed_drugs")

class Prescription(Base):
    __tablename__ = 'prescriptions'

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    doctor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(String, default='pending', nullable=False)  # e.g., 'pending', 'preparing', 'ready', 'dispensed'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="prescriptions")
    doctor = relationship("User", back_populates="prescriptions")
    prescribed_drugs = relationship("Drug", secondary=prescription_drug_association, back_populates="prescriptions")

# Example of how to create an engine and create all tables
# engine = create_engine('sqlite:///example.db')
# Base.metadata.create_all(engine)
