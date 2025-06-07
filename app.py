from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

# Initialize Flask app
app = Flask(__name__)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pharmacy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Optional: Disable modification tracking

# Initialize Flask-SQLAlchemy
db = SQLAlchemy(app)

# Import models (assuming models.py is in the same directory)
# It's important to import models after db is initialized if models use db.Model
from models import User, Patient, Drug, Prescription, PrescriptionDrugAssociation, Base

# Create database tables (run this once, typically)
# This needs to be within an application context
with app.app_context():
    Base.metadata.create_all(db.engine) # Use Base.metadata from models.py

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400

    username = data.get('username')
    password = data.get('password')

    if not username:
        return jsonify({"message": "Username is required"}), 400
    if not password:
        return jsonify({"message": "Password is required"}), 400

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        # In a real application, you would generate and return a JWT token here
        return jsonify({"message": "Login successful", "user_id": user.id, "role": user.role}), 200
    else:
        return jsonify({"message": "Invalid username or password"}), 401

@app.route('/prescriptions', methods=['POST'])
def create_prescription():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400

    patient_name = data.get('patient_name')
    patient_file_number = data.get('patient_file_number')
    doctor_id = data.get('doctor_id')
    drugs_data = data.get('drugs') # List of {"drug_id": X}

    if not all([patient_name, patient_file_number, doctor_id, drugs_data]):
        return jsonify({"message": "Missing required fields: patient_name, patient_file_number, doctor_id, drugs"}), 400

    if not isinstance(drugs_data, list) or not drugs_data:
        return jsonify({"message": "Drugs must be a non-empty list"}), 400

    # Validate doctor
    doctor = User.query.filter_by(id=doctor_id, role='doctor').first()
    if not doctor:
        return jsonify({"message": "Invalid or unauthorized doctor ID"}), 403

    # Find or create patient
    patient = Patient.query.filter_by(file_number=patient_file_number).first()
    if not patient:
        patient = Patient(name=patient_name, file_number=patient_file_number)
        db.session.add(patient)
        # We might want to commit here or let the final commit handle it.
        # For now, let's commit patient separately to ensure it has an ID if new.
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"message": "Error creating patient", "error": str(e)}), 500


    # Validate drugs and prepare drug objects
    prescribed_drugs_list = []
    for drug_info in drugs_data:
        drug_id = drug_info.get('drug_id')
        if not drug_id:
            return jsonify({"message": "Each drug entry must contain a 'drug_id'"}), 400

        drug = Drug.query.get(drug_id)
        if not drug:
            return jsonify({"message": f"Drug with ID {drug_id} not found"}), 400
        prescribed_drugs_list.append(drug)

    if not prescribed_drugs_list: # Should be caught by drugs_data check, but good to have
        return jsonify({"message": "No valid drugs provided for prescription"}), 400

    # Create Prescription
    new_prescription = Prescription(
        patient_id=patient.id,
        doctor_id=doctor.id
        # status is 'pending' by default
        # created_at is default by model
    )

    # Add drugs to the prescription
    for drug_obj in prescribed_drugs_list:
        new_prescription.prescribed_drugs.append(drug_obj)

    try:
        db.session.add(new_prescription)
        db.session.commit()
        return jsonify({
            "message": "Prescription created successfully",
            "prescription_id": new_prescription.id,
            "status": new_prescription.status,
            "created_at": new_prescription.created_at.isoformat()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating prescription", "error": str(e)}), 500


@app.route('/prescriptions/<int:prescription_id>', methods=['GET'])
def get_prescription(prescription_id):
    prescription = Prescription.query.get(prescription_id)
    if not prescription:
        return jsonify({"message": "Prescription not found"}), 404

    drugs_info = []
    for drug in prescription.prescribed_drugs:
        drugs_info.append({
            "id": drug.id,
            "name": drug.name,
            "strength": drug.strength,
            "instructions": drug.instructions,
            "warnings": drug.warnings
        })

    return jsonify({
        "id": prescription.id,
        "patient": {
            "id": prescription.patient.id,
            "name": prescription.patient.name,
            "file_number": prescription.patient.file_number
        },
        "doctor": {
            "id": prescription.doctor.id,
            "username": prescription.doctor.username # Assuming you want to show username
        },
        "status": prescription.status,
        "created_at": prescription.created_at.isoformat(),
        "prescribed_drugs": drugs_info
    }), 200


@app.route('/prescriptions/<int:prescription_id>/status', methods=['PUT'])
def update_prescription_status(prescription_id):
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400

    new_status = data.get('status')
    if not new_status:
        return jsonify({"message": "New status is required"}), 400

    prescription = Prescription.query.get(prescription_id)
    if not prescription:
        return jsonify({"message": "Prescription not found"}), 404

    # Optional: Add role-based access control here later if needed
    # For example, check if the logged-in user is a pharmacist

    prescription.status = new_status
    try:
        db.session.commit()

        # Prepare response data (similar to GET endpoint)
        drugs_info = []
        for drug in prescription.prescribed_drugs:
            drugs_info.append({
                "id": drug.id,
                "name": drug.name,
                "strength": drug.strength,
                "instructions": drug.instructions,
                "warnings": drug.warnings
            })

        return jsonify({
            "message": "Prescription status updated successfully",
            "prescription": {
                "id": prescription.id,
                "patient_id": prescription.patient_id,
                "doctor_id": prescription.doctor_id,
                "status": prescription.status,
                "created_at": prescription.created_at.isoformat(),
                "prescribed_drugs": drugs_info
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error updating prescription status", "error": str(e)}), 500

@app.route('/drugs', methods=['GET'])
def get_drugs():
    drugs = Drug.query.all()
    drugs_list = []
    for drug in drugs:
        drugs_list.append({
            "id": drug.id,
            "name": drug.name,
            "strength": drug.strength,
            "instructions": drug.instructions,
            "warnings": drug.warnings
        })
    return jsonify(drugs_list), 200

@app.route('/drugs', methods=['POST'])
def add_drug():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400

    name = data.get('name')
    strength = data.get('strength')
    instructions = data.get('instructions')
    warnings = data.get('warnings')

    if not all([name, strength, instructions, warnings]):
        return jsonify({"message": "Missing required fields: name, strength, instructions, warnings"}), 400

    # Optional: Check if drug already exists (e.g., by name and strength)
    # existing_drug = Drug.query.filter_by(name=name, strength=strength).first()
    # if existing_drug:
    #     return jsonify({"message": "Drug with this name and strength already exists"}), 409 # Conflict

    new_drug = Drug(
        name=name,
        strength=strength,
        instructions=instructions,
        warnings=warnings
    )

    try:
        db.session.add(new_drug)
        db.session.commit()
        return jsonify({
            "message": "Drug added successfully",
            "drug": {
                "id": new_drug.id,
                "name": new_drug.name,
                "strength": new_drug.strength,
                "instructions": new_drug.instructions,
                "warnings": new_drug.warnings
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        # A more specific error might be IntegrityError if a unique constraint was violated
        return jsonify({"message": "Error adding drug", "error": str(e)}), 500

@app.route('/prescriptions/<int:prescription_id>/label', methods=['GET'])
def get_prescription_label(prescription_id):
    prescription = Prescription.query.get(prescription_id)
    if not prescription:
        return jsonify({"message": "Prescription not found"}), 404

    labels = []
    today_date = datetime.date.today().isoformat()

    patient_name = prescription.patient.name
    patient_file_number = prescription.patient.file_number

    for drug in prescription.prescribed_drugs:
        label_string = (
            f"name of patient: {patient_name}\n"
            f"file number: {patient_file_number}\n"
            f"drug name: {drug.name}\n"
            f"strength: {drug.strength}\n"
            f"instructions: {drug.instructions}\n"
            f"warning: {drug.warnings}\n"
            f"date: {today_date}"
        )
        labels.append(label_string)

    return jsonify({
        "prescription_id": prescription_id,
        "labels": labels
    }), 200

@app.route('/dashboard/notifications', methods=['GET'])
def get_dashboard_notifications():
    pending_prescriptions = Prescription.query.filter_by(status='pending').order_by(Prescription.created_at.desc()).all()
    notifications = []
    for pres in pending_prescriptions:
        notifications.append({
            "id": pres.id,
            "patient_name": pres.patient.name,
            "created_at": pres.created_at.isoformat()
        })
    return jsonify(notifications), 200

@app.route('/dashboard/statistics/drug_prescriptions', methods=['GET'])
def get_drug_prescription_statistics():
    drugs = Drug.query.all()
    drug_counts = {}
    if not drugs:
            return jsonify(drug_counts), 200

    for drug in drugs:
        # len(drug.prescriptions) directly uses the relationship to count associated prescriptions.
        # This is efficient as SQLAlchemy handles the counting, often via a subquery or a join
        # depending on the relationship loading strategy.
        drug_counts[drug.name] = len(drug.prescriptions)

    return jsonify(drug_counts), 200

if __name__ == '__main__':
    # For development, you might want to add a test user if the DB is empty
    # Also, let's add some sample drugs for testing if they don't exist
    with app.app_context():
        if not User.query.filter_by(username='testdoctor').first():
            hashed_password = generate_password_hash('password123', method='pbkdf2:sha256')
            new_doctor = User(username='testdoctor', password_hash=hashed_password, role='doctor')
            db.session.add(new_doctor)
            db.session.commit()
            print("Test doctor created.")
        if not User.query.filter_by(username='testpharmacist').first():
            hashed_password = generate_password_hash('pharmacypass', method='pbkdf2:sha256')
            new_pharmacist = User(username='testpharmacist', password_hash=hashed_password, role='pharmacist')
            db.session.add(new_pharmacist)
            db.session.commit()
            print("Test pharmacist created.")

        # Add sample drugs
        if not Drug.query.filter_by(name='Amoxicillin').first():
            drug1 = Drug(name='Amoxicillin', strength='250mg', instructions='Take one tablet every 8 hours', warnings='May cause allergic reaction.')
            db.session.add(drug1)
        if not Drug.query.filter_by(name='Lisinopril').first():
            drug2 = Drug(name='Lisinopril', strength='10mg', instructions='Take one tablet daily', warnings='Monitor blood pressure.')
            db.session.add(drug2)
        if not Drug.query.filter_by(name='Metformin').first():
            drug3 = Drug(name='Metformin', strength='500mg', instructions='Take one tablet twice daily with meals', warnings='May cause gastrointestinal upset.')
            db.session.add(drug3)

        try:
            db.session.commit()
            print("Sample drugs checked/created.")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding sample drugs: {str(e)}")

    app.run(debug=True)
