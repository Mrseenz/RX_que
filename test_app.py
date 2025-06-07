import unittest
import json
from app import app, db # Assuming your Flask app instance is named 'app' and SQLAlchemy instance is 'db'
from models import User, Drug, Patient, Prescription # Import your models
from werkzeug.security import generate_password_hash

class PharmacyAppTests(unittest.TestCase):

    def setUp(self):
        """Set up test variables."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        # app.config['WTF_CSRF_ENABLED'] = False # If you use Flask-WTF CSRF protection

        self.client = app.test_client()

        with app.app_context():
            db.create_all()
            self.populate_test_data()

    def tearDown(self):
        """Executed after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def populate_test_data(self):
        """Populates the database with initial test data."""
        # Users
        hashed_password_doctor = generate_password_hash('doctorpass', method='pbkdf2:sha256')
        self.doctor = User(username='testdoc', password_hash=hashed_password_doctor, role='doctor')

        hashed_password_pharmacist = generate_password_hash('pharmacistpass', method='pbkdf2:sha256')
        self.pharmacist = User(username='testpharmacist', password_hash=hashed_password_pharmacist, role='pharmacist')

        db.session.add_all([self.doctor, self.pharmacist])
        db.session.commit() # Commit users to get IDs

        # Drugs
        self.drug1 = Drug(name='Amoxicillin', strength='250mg', instructions='Take 1 every 8 hours', warnings='Allergic reactions possible')
        self.drug2 = Drug(name='Panadol', strength='500mg', instructions='2 tablets every 4-6 hours', warnings='Max 8 tablets/day')
        self.drug3 = Drug(name='Lisinopril', strength='10mg', instructions='1 tablet daily', warnings='Monitor blood pressure')
        db.session.add_all([self.drug1, self.drug2, self.drug3])

        # Patient
        self.patient1 = Patient(name="John Doe", file_number="JD001")
        db.session.add(self.patient1)

        db.session.commit()


    # --- Test Authentication ---
    def test_login_successful_doctor(self):
        response = self.client.post('/login', json={'username': 'testdoc', 'password': 'doctorpass'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Login successful')
        self.assertEqual(data['role'], 'doctor')

    def test_login_successful_pharmacist(self):
        response = self.client.post('/login', json={'username': 'testpharmacist', 'password': 'pharmacistpass'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Login successful')
        self.assertEqual(data['role'], 'pharmacist')

    def test_login_invalid_credentials(self):
        response = self.client.post('/login', json={'username': 'testdoc', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invalid username or password')

    def test_login_missing_username(self):
        response = self.client.post('/login', json={'password': 'doctorpass'})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Username is required')

    def test_login_missing_password(self):
        response = self.client.post('/login', json={'username': 'testdoc'})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Password is required')

    # --- Test Drugs Endpoints ---
    def test_get_drugs(self):
        response = self.client.get('/drugs')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 3) # We added 3 drugs
        self.assertIn('Amoxicillin', [d['name'] for d in data])

    def test_add_new_drug(self):
        new_drug_data = {
            "name": "Ibuprofen",
            "strength": "200mg",
            "instructions": "As needed for pain",
            "warnings": "Do not exceed daily limit"
        }
        response = self.client.post('/drugs', json=new_drug_data)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Drug added successfully')
        self.assertEqual(data['drug']['name'], 'Ibuprofen')

        # Verify drug is in DB
        with app.app_context():
            drug = Drug.query.filter_by(name='Ibuprofen').first()
            self.assertIsNotNone(drug)
            self.assertEqual(drug.strength, '200mg')

    def test_add_drug_missing_data(self):
        response = self.client.post('/drugs', json={"name": "MissingInfoDrug"})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Missing required fields: name, strength, instructions, warnings')

    # --- Test Prescriptions Endpoints ---
    def test_create_prescription_new_patient(self):
        prescription_data = {
            "patient_name": "Jane Smith",
            "patient_file_number": "JS001",
            "doctor_id": self.doctor.id,
            "drugs": [{"drug_id": self.drug1.id}, {"drug_id": self.drug2.id}]
        }
        response = self.client.post('/prescriptions', json=prescription_data)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Prescription created successfully')
        prescription_id = data['prescription_id']

        with app.app_context():
            pres = Prescription.query.get(prescription_id)
            self.assertIsNotNone(pres)
            self.assertEqual(pres.patient.name, "Jane Smith")
            self.assertEqual(len(pres.prescribed_drugs), 2)
            self.assertIn(self.drug1, pres.prescribed_drugs)

    def test_create_prescription_existing_patient(self):
        prescription_data = {
            "patient_name": "John Doe", # This name might differ from DB, file_number is key
            "patient_file_number": self.patient1.file_number,
            "doctor_id": self.doctor.id,
            "drugs": [{"drug_id": self.drug3.id}]
        }
        response = self.client.post('/prescriptions', json=prescription_data)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        prescription_id = data['prescription_id']

        with app.app_context():
            pres = Prescription.query.get(prescription_id)
            self.assertIsNotNone(pres)
            self.assertEqual(pres.patient_id, self.patient1.id) # Check if existing patient was used
            self.assertEqual(len(pres.prescribed_drugs), 1)

    def test_create_prescription_invalid_doctor_id(self):
        prescription_data = {
            "patient_name": "Test Patient",
            "patient_file_number": "TP001",
            "doctor_id": 999, # Invalid ID
            "drugs": [{"drug_id": self.drug1.id}]
        }
        response = self.client.post('/prescriptions', json=prescription_data)
        self.assertEqual(response.status_code, 403) # Or 400 depending on implementation
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invalid or unauthorized doctor ID')

    def test_create_prescription_invalid_drug_id(self):
        prescription_data = {
            "patient_name": "Test Patient",
            "patient_file_number": "TP002",
            "doctor_id": self.doctor.id,
            "drugs": [{"drug_id": 999}] # Invalid ID
        }
        response = self.client.post('/prescriptions', json=prescription_data)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Drug with ID 999 not found', data['message'])

    def test_get_prescription_by_id(self):
        # First, create a prescription to fetch
        pres = Prescription(patient_id=self.patient1.id, doctor_id=self.doctor.id, status='pending')
        pres.prescribed_drugs.append(self.drug1)
        with app.app_context():
            db.session.add(pres)
            db.session.commit()
            pres_id = pres.id

        response = self.client.get(f'/prescriptions/{pres_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['id'], pres_id)
        self.assertEqual(data['patient']['name'], self.patient1.name)
        self.assertEqual(len(data['prescribed_drugs']), 1)
        self.assertEqual(data['prescribed_drugs'][0]['name'], self.drug1.name)

    def test_update_prescription_status(self):
        pres = Prescription(patient_id=self.patient1.id, doctor_id=self.doctor.id, status='pending')
        with app.app_context():
            db.session.add(pres)
            db.session.commit()
            pres_id = pres.id

        response = self.client.put(f'/prescriptions/{pres_id}/status', json={"status": "ready"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Prescription status updated successfully')
        self.assertEqual(data['prescription']['status'], 'ready')

        with app.app_context():
            updated_pres = Prescription.query.get(pres_id)
            self.assertEqual(updated_pres.status, 'ready')

    # --- Test Labels Endpoint ---
    def test_get_prescription_label(self):
        pres = Prescription(patient_id=self.patient1.id, doctor_id=self.doctor.id)
        pres.prescribed_drugs.append(self.drug1)
        pres.prescribed_drugs.append(self.drug2)
        with app.app_context():
            db.session.add(pres)
            db.session.commit()
            pres_id = pres.id

        response = self.client.get(f'/prescriptions/{pres_id}/label')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['prescription_id'], pres_id)
        self.assertEqual(len(data['labels']), 2)

        label1_content = data['labels'][0]
        self.assertIn(f"name of patient: {self.patient1.name}", label1_content)
        self.assertIn(f"file number: {self.patient1.file_number}", label1_content)
        self.assertIn(f"drug name: {self.drug1.name}", label1_content)
        self.assertIn(f"strength: {self.drug1.strength}", label1_content)
        self.assertIn(f"instructions: {self.drug1.instructions}", label1_content)
        self.assertIn(f"warning: {self.drug1.warnings}", label1_content)
        self.assertIn("date:", label1_content) # Check for date presence

    # --- Test Dashboard Endpoints ---
    def test_get_dashboard_notifications_pending(self):
        # Ensure at least one pending prescription
        pres = Prescription(patient_id=self.patient1.id, doctor_id=self.doctor.id, status='pending')
        with app.app_context():
            db.session.add(pres)
            db.session.commit()

        response = self.client.get('/dashboard/notifications')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(len(data) > 0)
        self.assertEqual(data[0]['patient_name'], self.patient1.name)
        self.assertEqual(data[0]['id'], pres.id)

    def test_get_dashboard_notifications_none_pending(self):
         # Make sure no prescription is pending
        with app.app_context():
            Prescription.query.delete() # Clear any existing
            pres_ready = Prescription(patient_id=self.patient1.id, doctor_id=self.doctor.id, status='ready')
            db.session.add(pres_ready)
            db.session.commit()

        response = self.client.get('/dashboard/notifications')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 0)


    def test_get_drug_prescription_statistics(self):
        # Create a prescription with drug1 and drug2
        pres1 = Prescription(patient_id=self.patient1.id, doctor_id=self.doctor.id)
        pres1.prescribed_drugs.append(self.drug1)
        pres1.prescribed_drugs.append(self.drug2)

        # Create another prescription with drug1
        pres2 = Prescription(patient_id=self.patient1.id, doctor_id=self.doctor.id) # Assuming another patient or same for simplicity
        pres2.prescribed_drugs.append(self.drug1)

        with app.app_context():
            db.session.add_all([pres1, pres2])
            db.session.commit()

        response = self.client.get('/dashboard/statistics/drug_prescriptions')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertEqual(data[self.drug1.name], 2)
        self.assertEqual(data[self.drug2.name], 1)
        self.assertEqual(data[self.drug3.name], 0) # drug3 not in any prescription

if __name__ == '__main__':
    unittest.main()
